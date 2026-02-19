from collections import OrderedDict

from rest_framework import serializers

from .models import Exercise, ScheduledWorkout, Workout, WorkoutSet


class ExerciseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = ['id', 'name', 'muscle_group', 'description', 'is_custom', 'user']
        read_only_fields = ['user', 'is_custom']


class WorkoutSetSerializer(serializers.ModelSerializer):
    exercise_name = serializers.CharField(source='exercise.name', read_only=True)

    class Meta:
        model = WorkoutSet
        fields = ['id', 'workout', 'exercise', 'exercise_name', 'weight', 'reps', 'rir', 'created_at']
        read_only_fields = ['created_at']


class SetInGroupSerializer(serializers.ModelSerializer):
    """Подход внутри группы (без exercise — он уже в родителе)."""

    class Meta:
        model = WorkoutSet
        fields = ['id', 'weight', 'reps', 'rir']


class WorkoutListSerializer(serializers.ModelSerializer):
    """Краткий — для списка тренировок."""
    total_sets = serializers.IntegerField(source='sets.count', read_only=True)
    total_volume = serializers.SerializerMethodField()

    class Meta:
        model = Workout
        fields = ['id', 'start_time', 'end_time', 'status', 'note', 'total_sets', 'total_volume']

    def get_total_volume(self, obj):
        """Общий тоннаж тренировки (вес × повторения)."""
        return sum(s.weight * s.reps for s in obj.sets.all())


class WorkoutDetailSerializer(serializers.ModelSerializer):
    """Подробный — подходы сгруппированы по упражнениям."""
    exercises = serializers.SerializerMethodField()
    duration_minutes = serializers.SerializerMethodField()
    total_volume = serializers.SerializerMethodField()

    class Meta:
        model = Workout
        fields = ['id', 'start_time', 'end_time', 'status', 'note',
                  'duration_minutes', 'total_volume', 'exercises']

    def get_exercises(self, obj):
        """Группировка подходов по упражнениям."""
        sets = obj.sets.select_related('exercise').order_by('created_at')
        groups = OrderedDict()
        for s in sets:
            ex_id = s.exercise_id
            if ex_id not in groups:
                groups[ex_id] = {
                    'exercise_id': ex_id,
                    'exercise_name': s.exercise.name,
                    'muscle_group': s.exercise.muscle_group,
                    'sets': [],
                }
            groups[ex_id]['sets'].append(SetInGroupSerializer(s).data)
        return list(groups.values())

    def get_duration_minutes(self, obj):
        if obj.end_time and obj.start_time:
            delta = obj.end_time - obj.start_time
            return round(delta.total_seconds() / 60)
        return None

    def get_total_volume(self, obj):
        return sum(s.weight * s.reps for s in obj.sets.all())


class ScheduledWorkoutSerializer(serializers.ModelSerializer):
    exercises = ExerciseSerializer(many=True, read_only=True)
    exercise_ids = serializers.PrimaryKeyRelatedField(
        queryset=Exercise.objects.all(),
        many=True,
        write_only=True,
        source='exercises',
        required=False,
    )
    is_completed = serializers.BooleanField(read_only=True)

    class Meta:
        model = ScheduledWorkout
        fields = [
            'id', 'date', 'time', 'title', 'exercises', 'exercise_ids',
            'note', 'is_completed', 'workout', 'notify_before',
        ]
        read_only_fields = ['workout']


class CalendarDaySerializer(serializers.Serializer):
    """Один день в календаре."""
    date = serializers.DateField()
    completed_workouts = WorkoutListSerializer(many=True)
    scheduled = ScheduledWorkoutSerializer(many=True)
