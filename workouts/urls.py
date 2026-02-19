from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ExerciseViewSet,
    WorkoutViewSet,
    WorkoutSetViewSet,
    ScheduledWorkoutViewSet,
    CalendarView,
    UpcomingNotificationsView,
    VolumeAnalyticsView,
    MaxWeightAnalyticsView,
    PersonalRecordsView,
)

router = DefaultRouter()
router.register('exercises', ExerciseViewSet, basename='exercise')
router.register('workouts', WorkoutViewSet, basename='workout')
router.register('sets', WorkoutSetViewSet, basename='workoutset')
router.register('schedule', ScheduledWorkoutViewSet, basename='schedule')

urlpatterns = router.urls + [
    path('calendar/', CalendarView.as_view(), name='calendar'),
    path('notifications/upcoming/', UpcomingNotificationsView.as_view(), name='notifications-upcoming'),
    path('analytics/volume/', VolumeAnalyticsView.as_view(), name='analytics-volume'),
    path('analytics/max/', MaxWeightAnalyticsView.as_view(), name='analytics-max'),
    path('analytics/records/', PersonalRecordsView.as_view(), name='analytics-records'),
]
