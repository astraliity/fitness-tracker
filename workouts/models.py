from django.db import models
from django.contrib.auth.models import User


class Exercise(models.Model):
    """Справочник упражнений (общие + пользовательские)."""

    MUSCLE_CHOICES = [
        ('CHEST', 'Грудь'),
        ('BACK', 'Спина'),
        ('SHOULDERS', 'Плечи'),
        ('BICEPS', 'Бицепс'),
        ('TRICEPS', 'Трицепс'),
        ('FOREARMS', 'Предплечья'),
        ('QUADS', 'Квадрицепс'),
        ('HAMSTRINGS', 'Бицепс бедра'),
        ('GLUTES', 'Ягодицы'),
        ('CALVES', 'Икры'),
        ('CORE', 'Пресс'),
        ('TRAPS', 'Трапеция'),
        ('CARDIO', 'Кардио'),
    ]

    name = models.CharField('Название', max_length=100)
    muscle_group = models.CharField(
        'Группа мышц', max_length=20, choices=MUSCLE_CHOICES,
    )
    description = models.TextField('Описание', blank=True)
    is_custom = models.BooleanField('Пользовательское', default=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='Автор',
        related_name='exercises',
    )

    class Meta:
        verbose_name = 'Упражнение'
        verbose_name_plural = 'Упражнения'
        ordering = ['name']

    def __str__(self):
        return self.name


class Workout(models.Model):
    """Тренировочная сессия."""

    STATUS_CHOICES = [
        ('STARTED', 'Начата'),
        ('FINISHED', 'Завершена'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='workouts',
    )
    start_time = models.DateTimeField('Начало', auto_now_add=True)
    end_time = models.DateTimeField('Конец', null=True, blank=True)
    status = models.CharField(
        'Статус', max_length=20, choices=STATUS_CHOICES, default='STARTED',
    )
    note = models.TextField('Заметка', blank=True)

    class Meta:
        verbose_name = 'Тренировка'
        verbose_name_plural = 'Тренировки'
        ordering = ['-start_time']

    def __str__(self):
        return f'Тренировка {self.pk} — {self.start_time:%d.%m.%Y %H:%M}'


class WorkoutSet(models.Model):
    """Один подход в тренировке."""

    workout = models.ForeignKey(
        Workout,
        on_delete=models.CASCADE,
        verbose_name='Тренировка',
        related_name='sets',
    )
    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.CASCADE,
        verbose_name='Упражнение',
        related_name='sets',
    )
    weight = models.FloatField('Вес (кг)')
    reps = models.PositiveIntegerField('Повторения')
    rir = models.PositiveIntegerField('RIR', null=True, blank=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Подход'
        verbose_name_plural = 'Подходы'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.exercise.name}: {self.weight}кг × {self.reps}'


class ScheduledWorkout(models.Model):
    """Запланированная тренировка (расписание)."""

    DAY_CHOICES = [
        (0, 'Понедельник'),
        (1, 'Вторник'),
        (2, 'Среда'),
        (3, 'Четверг'),
        (4, 'Пятница'),
        (5, 'Суббота'),
        (6, 'Воскресенье'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='scheduled_workouts',
    )
    date = models.DateField('Дата')
    time = models.TimeField('Время', null=True, blank=True)
    title = models.CharField('Название', max_length=100)
    exercises = models.ManyToManyField(
        Exercise,
        blank=True,
        verbose_name='Упражнения',
        related_name='scheduled_workouts',
    )
    note = models.TextField('Заметка', blank=True)
    is_completed = models.BooleanField('Выполнена', default=False)
    workout = models.OneToOneField(
        Workout,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Фактическая тренировка',
        related_name='schedule',
    )
    notify_before = models.PositiveIntegerField(
        'Напомнить за (минут)',
        default=30,
    )

    class Meta:
        verbose_name = 'Запланированная тренировка'
        verbose_name_plural = 'Запланированные тренировки'
        ordering = ['date', 'time']

    def __str__(self):
        return f'{self.date} — {self.title}'
