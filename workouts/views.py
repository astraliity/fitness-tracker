from collections import defaultdict
from datetime import date, timedelta

from django.db.models import Sum, Max, F
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Exercise, ScheduledWorkout, Workout, WorkoutSet
from .serializers import (
    ExerciseSerializer,
    ScheduledWorkoutSerializer,
    WorkoutListSerializer,
    WorkoutDetailSerializer,
    WorkoutSetSerializer,
)


class ExerciseViewSet(viewsets.ModelViewSet):
    """CRUD для упражнений."""
    serializer_class = ExerciseSerializer

    def get_queryset(self):
        return Exercise.objects.filter(
            user__isnull=True,
        ) | Exercise.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, is_custom=True)


class WorkoutViewSet(viewsets.ModelViewSet):
    """CRUD для тренировок."""

    def get_queryset(self):
        return Workout.objects.filter(
            user=self.request.user,
        ).prefetch_related('sets', 'sets__exercise')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return WorkoutDetailSerializer
        return WorkoutListSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def finish(self, request, pk=None):
        """POST /api/workouts/{id}/finish/ — завершить тренировку."""
        workout = self.get_object()
        workout.status = 'FINISHED'
        workout.end_time = timezone.now()
        workout.save()
        return Response(WorkoutDetailSerializer(workout).data)


class WorkoutSetViewSet(viewsets.ModelViewSet):
    """CRUD для подходов."""
    serializer_class = WorkoutSetSerializer

    def get_queryset(self):
        return WorkoutSet.objects.filter(
            workout__user=self.request.user,
        ).select_related('exercise')


# ============================================================
# Расписание тренировок
# ============================================================

class ScheduledWorkoutViewSet(viewsets.ModelViewSet):
    """CRUD для запланированных тренировок."""
    serializer_class = ScheduledWorkoutSerializer

    def get_queryset(self):
        return ScheduledWorkout.objects.filter(
            user=self.request.user,
        ).prefetch_related('exercises')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """POST /api/schedule/{id}/complete/ — отметить как выполненную."""
        scheduled = self.get_object()
        scheduled.is_completed = True
        scheduled.save()
        return Response(ScheduledWorkoutSerializer(scheduled).data)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """
        POST /api/schedule/{id}/start/ — начать тренировку из расписания.
        Создаёт реальную Workout и привязывает к расписанию.
        """
        scheduled = self.get_object()

        if scheduled.workout:
            return Response(
                {'error': 'Тренировка уже начата'},
                status=400,
            )

        workout = Workout.objects.create(user=request.user)
        scheduled.workout = workout
        scheduled.save()

        return Response({
            'scheduled': ScheduledWorkoutSerializer(scheduled).data,
            'workout_id': workout.pk,
        }, status=201)


# ============================================================
# Календарь
# ============================================================

class CalendarView(APIView):
    """
    GET /api/calendar/?start=2026-02-01&end=2026-02-28

    Возвращает данные по дням: выполненные тренировки + расписание.
    """

    def get(self, request):
        start_str = request.query_params.get('start')
        end_str = request.query_params.get('end')

        if start_str and end_str:
            start = date.fromisoformat(start_str)
            end = date.fromisoformat(end_str)
        else:
            today = date.today()
            start = today.replace(day=1)
            # Последний день месяца
            next_month = (start + timedelta(days=32)).replace(day=1)
            end = next_month - timedelta(days=1)

        # Выполненные тренировки за период
        workouts = (
            Workout.objects.filter(
                user=request.user,
                start_time__date__gte=start,
                start_time__date__lte=end,
            )
            .prefetch_related('sets', 'sets__exercise')
            .order_by('start_time')
        )

        # Запланированные тренировки за период
        scheduled = (
            ScheduledWorkout.objects.filter(
                user=request.user,
                date__gte=start,
                date__lte=end,
            )
            .prefetch_related('exercises')
            .order_by('date', 'time')
        )

        # Группировка по дням
        days = defaultdict(lambda: {'completed': [], 'scheduled': []})

        for w in workouts:
            d = w.start_time.date()
            days[d]['completed'].append(WorkoutListSerializer(w).data)

        for s in scheduled:
            days[s.date]['scheduled'].append(
                ScheduledWorkoutSerializer(s).data,
            )

        # Формируем ответ
        result = []
        current = start
        while current <= end:
            day_data = days.get(current, {'completed': [], 'scheduled': []})
            result.append({
                'date': current.isoformat(),
                'has_workout': bool(day_data['completed']),
                'has_scheduled': bool(day_data['scheduled']),
                'completed_workouts': day_data['completed'],
                'scheduled': day_data['scheduled'],
            })
            current += timedelta(days=1)

        return Response(result)


class UpcomingNotificationsView(APIView):
    """
    GET /api/notifications/upcoming/

    Запланированные тренировки на ближайшие 24 часа.
    Клиент использует notify_before для показа уведомлений.
    """

    def get(self, request):
        now = timezone.now()
        tomorrow = now + timedelta(hours=24)

        upcoming = (
            ScheduledWorkout.objects.filter(
                user=request.user,
                date__gte=now.date(),
                date__lte=tomorrow.date(),
                is_completed=False,
            )
            .prefetch_related('exercises')
            .order_by('date', 'time')
        )

        return Response(ScheduledWorkoutSerializer(upcoming, many=True).data)


# ============================================================
# Аналитика
# ============================================================

class VolumeAnalyticsView(APIView):
    """
    GET /api/analytics/volume/?days=30

    График тоннажа по дням.
    """

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)

        data = (
            WorkoutSet.objects
            .filter(
                workout__user=request.user,
                workout__start_time__gte=since,
            )
            .annotate(date=TruncDate('workout__start_time'))
            .values('date')
            .annotate(volume=Sum(F('weight') * F('reps')))
            .order_by('date')
        )

        return Response([
            {'date': row['date'], 'volume': round(row['volume'], 1)}
            for row in data
        ])


class MaxWeightAnalyticsView(APIView):
    """
    GET /api/analytics/max/?exercise_id=3&days=90

    График максимального веса по дням для упражнения.
    """

    def get(self, request):
        exercise_id = request.query_params.get('exercise_id')
        if not exercise_id:
            return Response(
                {'error': 'exercise_id is required'}, status=400,
            )

        days = int(request.query_params.get('days', 90))
        since = timezone.now() - timedelta(days=days)

        data = (
            WorkoutSet.objects
            .filter(
                workout__user=request.user,
                exercise_id=exercise_id,
                workout__start_time__gte=since,
            )
            .annotate(date=TruncDate('workout__start_time'))
            .values('date')
            .annotate(max_weight=Max('weight'))
            .order_by('date')
        )

        return Response([
            {'date': row['date'], 'max_weight': row['max_weight']}
            for row in data
        ])


class PersonalRecordsView(APIView):
    """
    GET /api/analytics/records/

    Личные рекорды по каждому упражнению.
    """

    def get(self, request):
        data = (
            WorkoutSet.objects
            .filter(workout__user=request.user)
            .values('exercise_id', 'exercise__name', 'exercise__muscle_group')
            .annotate(max_weight=Max('weight'))
            .order_by('exercise__name')
        )

        return Response([
            {
                'exercise_id': row['exercise_id'],
                'exercise_name': row['exercise__name'],
                'muscle_group': row['exercise__muscle_group'],
                'max_weight': row['max_weight'],
            }
            for row in data
        ])
