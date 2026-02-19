from django.contrib import admin

from .models import Exercise, ScheduledWorkout, Workout, WorkoutSet


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ['name', 'muscle_group', 'is_custom', 'user']
    list_filter = ['muscle_group', 'is_custom']
    search_fields = ['name']


class WorkoutSetInline(admin.TabularInline):
    model = WorkoutSet
    extra = 0


@admin.register(Workout)
class WorkoutAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'user', 'status', 'start_time']
    list_filter = ['status', 'user']
    inlines = [WorkoutSetInline]


@admin.register(WorkoutSet)
class WorkoutSetAdmin(admin.ModelAdmin):
    list_display = ['exercise', 'weight', 'reps', 'workout', 'created_at']
    list_filter = ['exercise__muscle_group']


@admin.register(ScheduledWorkout)
class ScheduledWorkoutAdmin(admin.ModelAdmin):
    list_display = ['date', 'time', 'title', 'user', 'is_completed']
    list_filter = ['is_completed', 'user', 'date']
    filter_horizontal = ['exercises']
