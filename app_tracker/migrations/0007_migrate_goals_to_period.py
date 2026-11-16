from django.db import migrations


def migrate_goals(apps, schema_editor):
    Participant = apps.get_model('app_tracker', 'Participant')
    GoalPeriod = apps.get_model('app_tracker', 'GoalPeriod')

    for participant in Participant.objects.all():
        # Если у участника есть старые цели, переносим их
        if participant.goal_1 or participant.goal_2 or participant.goal_3:
            month = participant.goals_month or "2026-11"

            GoalPeriod.objects.get_or_create(
                participant=participant,
                month=month,
                defaults={
                    'goal_1': participant.goal_1 or "",
                    'goal_2': participant.goal_2 or "",
                    'goal_3': participant.goal_3 or "",
                    'status': 'active'
                }
            )


def reverse_migrate(apps, schema_editor):
    # Откат миграции (если понадобится)
    pass


class Migration(migrations.Migration):
    dependencies = [
        # ВАЖНО: тут должно быть имя файла из Шага 1!
        ('app_tracker', '0006_report_goal_1_note_report_goal_2_note_and_more'),
    ]

    operations = [
        migrations.RunPython(migrate_goals, reverse_migrate),
    ]
