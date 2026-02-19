from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Exercise, ScheduledWorkout, Workout, WorkoutSet


class ExerciseAPITest(APITestCase):
    """Тесты CRUD упражнений."""

    def setUp(self):
        self.user = User.objects.create_user('athlete', password='test123')
        self.client.force_authenticate(self.user)
        self.public_exercise = Exercise.objects.create(
            name='Жим лежа', muscle_group='CHEST',
        )

    def test_list_exercises(self):
        """Список включает общие упражнения."""
        response = self.client.get('/api/exercises/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [e['name'] for e in response.data]
        self.assertIn('Жим лежа', names)

    def test_create_custom_exercise(self):
        """Создание пользовательского упражнения."""
        data = {
            'name': 'Моё упражнение',
            'muscle_group': 'BACK',
            'description': 'Тест',
        }
        response = self.client.post('/api/exercises/', data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['is_custom'])
        self.assertEqual(response.data['user'], self.user.id)

    def test_other_user_cant_see_my_exercise(self):
        """Чужой пользователь не видит мои упражнения."""
        Exercise.objects.create(
            name='Секретное', muscle_group='CORE',
            is_custom=True, user=self.user,
        )

        other = User.objects.create_user('other', password='test123')
        self.client.force_authenticate(other)
        response = self.client.get('/api/exercises/')

        names = [e['name'] for e in response.data]
        self.assertNotIn('Секретное', names)
        self.assertIn('Жим лежа', names)  # общее — видно всем


class WorkoutAPITest(APITestCase):
    """Тесты CRUD тренировок."""

    def setUp(self):
        self.user = User.objects.create_user('athlete', password='test123')
        self.client.force_authenticate(self.user)

    def test_create_workout(self):
        """Создание тренировки → статус STARTED."""
        response = self.client.post('/api/workouts/', {'note': 'Грудь'})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'STARTED')
        self.assertIsNotNone(response.data['start_time'])

    def test_finish_workout(self):
        """Завершение тренировки → статус FINISHED + end_time."""
        workout = Workout.objects.create(user=self.user)
        response = self.client.post(f'/api/workouts/{workout.pk}/finish/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'FINISHED')
        self.assertIsNotNone(response.data['end_time'])

    def test_list_only_my_workouts(self):
        """Пользователь видит только СВОИ тренировки."""
        Workout.objects.create(user=self.user, note='Моя')

        other = User.objects.create_user('other', password='test123')
        Workout.objects.create(user=other, note='Чужая')

        response = self.client.get('/api/workouts/')

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['note'], 'Моя')

    def test_workout_detail_has_exercises(self):
        """Детали тренировки содержат подходы, сгруппированные по упражнениям."""
        exercise = Exercise.objects.create(
            name='Приседания', muscle_group='QUADS',
        )
        workout = Workout.objects.create(user=self.user)
        WorkoutSet.objects.create(
            workout=workout, exercise=exercise, weight=100, reps=5,
        )
        WorkoutSet.objects.create(
            workout=workout, exercise=exercise, weight=110, reps=3,
        )

        response = self.client.get(f'/api/workouts/{workout.pk}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['exercises']), 1)
        self.assertEqual(response.data['exercises'][0]['exercise_name'], 'Приседания')
        self.assertEqual(len(response.data['exercises'][0]['sets']), 2)

    def test_workout_total_volume(self):
        """Тоннаж считается правильно: sum(weight * reps)."""
        exercise = Exercise.objects.create(
            name='Жим', muscle_group='CHEST',
        )
        workout = Workout.objects.create(user=self.user)
        WorkoutSet.objects.create(
            workout=workout, exercise=exercise, weight=80, reps=10,
        )  # 800
        WorkoutSet.objects.create(
            workout=workout, exercise=exercise, weight=90, reps=5,
        )  # 450

        response = self.client.get(f'/api/workouts/{workout.pk}/')

        self.assertEqual(response.data['total_volume'], 1250.0)


class WorkoutSetAPITest(APITestCase):
    """Тесты подходов."""

    def setUp(self):
        self.user = User.objects.create_user('athlete', password='test123')
        self.client.force_authenticate(self.user)
        self.exercise = Exercise.objects.create(
            name='Подтягивания', muscle_group='BACK',
        )
        self.workout = Workout.objects.create(user=self.user)

    def test_create_set(self):
        """Создание подхода."""
        data = {
            'workout': self.workout.pk,
            'exercise': self.exercise.pk,
            'weight': 0,
            'reps': 12,
        }
        response = self.client.post('/api/sets/', data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['exercise_name'], 'Подтягивания')

    def test_set_has_exercise_name(self):
        """В ответе есть exercise_name (вычисляемое поле)."""
        ws = WorkoutSet.objects.create(
            workout=self.workout, exercise=self.exercise,
            weight=10, reps=8,
        )
        response = self.client.get(f'/api/sets/{ws.pk}/')

        self.assertEqual(response.data['exercise_name'], 'Подтягивания')


class ScheduleAPITest(APITestCase):
    """Тесты расписания тренировок."""

    def setUp(self):
        self.user = User.objects.create_user('athlete', password='test123')
        self.client.force_authenticate(self.user)

    def test_create_schedule(self):
        """Создание запланированной тренировки."""
        data = {
            'date': '2026-02-20',
            'time': '18:00',
            'title': 'Спина + бицепс',
        }
        response = self.client.post('/api/schedule/', data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data['is_completed'])

    def test_start_scheduled_workout(self):
        """Начало тренировки из расписания → создаёт реальную Workout."""
        scheduled = ScheduledWorkout.objects.create(
            user=self.user, date='2026-02-20', title='Грудь',
        )
        response = self.client.post(f'/api/schedule/{scheduled.pk}/start/')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('workout_id', response.data)

        # Проверяем что Workout реально создался
        workout_id = response.data['workout_id']
        self.assertTrue(Workout.objects.filter(pk=workout_id).exists())

    def test_start_already_started(self):
        """Повторный старт → ошибка 400."""
        workout = Workout.objects.create(user=self.user)
        scheduled = ScheduledWorkout.objects.create(
            user=self.user, date='2026-02-20',
            title='Грудь', workout=workout,
        )
        response = self.client.post(f'/api/schedule/{scheduled.pk}/start/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_complete_schedule(self):
        """Отметка расписания как выполненного."""
        scheduled = ScheduledWorkout.objects.create(
            user=self.user, date='2026-02-20', title='Ноги',
        )
        response = self.client.post(f'/api/schedule/{scheduled.pk}/complete/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_completed'])


class AnalyticsAPITest(APITestCase):
    """Тесты аналитики."""

    def setUp(self):
        self.user = User.objects.create_user('athlete', password='test123')
        self.client.force_authenticate(self.user)
        self.exercise = Exercise.objects.create(
            name='Жим лежа', muscle_group='CHEST',
        )
        self.workout = Workout.objects.create(user=self.user)
        WorkoutSet.objects.create(
            workout=self.workout, exercise=self.exercise,
            weight=80, reps=10,
        )
        WorkoutSet.objects.create(
            workout=self.workout, exercise=self.exercise,
            weight=100, reps=5,
        )

    def test_volume_analytics(self):
        """Тоннаж по дням возвращает данные."""
        response = self.client.get('/api/analytics/volume/?days=30')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # 1 день
        # 80*10 + 100*5 = 1300
        self.assertEqual(response.data[0]['volume'], 1300.0)

    def test_max_weight_analytics(self):
        """Максимальный вес по упражнению."""
        response = self.client.get(
            f'/api/analytics/max/?exercise_id={self.exercise.pk}&days=30',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['max_weight'], 100.0)

    def test_max_weight_requires_exercise_id(self):
        """Без exercise_id → 400."""
        response = self.client.get('/api/analytics/max/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_personal_records(self):
        """Личные рекорды по упражнениям."""
        response = self.client.get('/api/analytics/records/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['exercise_name'], 'Жим лежа')
        self.assertEqual(response.data[0]['max_weight'], 100.0)


class CalendarAPITest(APITestCase):
    """Тесты календаря."""

    def setUp(self):
        self.user = User.objects.create_user('athlete', password='test123')
        self.client.force_authenticate(self.user)

    def test_calendar_returns_days(self):
        """Календарь возвращает массив дней."""
        response = self.client.get(
            '/api/calendar/?start=2026-02-01&end=2026-02-28',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 28)  # 28 дней февраля

    def test_calendar_shows_workout(self):
        """День с тренировкой имеет has_workout=True."""
        Workout.objects.create(user=self.user)  # сегодня

        response = self.client.get('/api/calendar/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        today_data = [d for d in response.data if d['has_workout']]
        self.assertGreaterEqual(len(today_data), 1)
