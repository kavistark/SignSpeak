"""
URL routing for the translator Django app.
"""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/diagnostics', views.diagnostics, name='diagnostics'),
    path('api/vocabulary', views.vocabulary, name='vocabulary'),
    path('api/translate', views.quick_translate, name='quick_translate'),
    path('api/process', views.process_job, name='process_job'),
    path('api/stream/<str:job_id>', views.stream_events, name='stream_events'),
    path('api/result/<str:job_id>', views.job_result, name='job_result'),
    path('api/poll/<str:job_id>', views.poll_status, name='poll_status'),
    path('api/keypoints/<str:job_id>', views.keypoints_json, name='keypoints_json'),
    path('static/outputs/<str:job_id>/<str:filename>', views.serve_output_file, name='serve_output_file'),
]
