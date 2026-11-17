from django.db import migrations


def migrate_goals(apps, schema_editor):
    Participant = apps.get_model('app_tracker', 'Participant')
    GoalPeriod = apps.get_model('app_tracker', 'GoalPeriod')

    for participant in Participant.objects.all():
        if not participant.goals_month:
            continue
        if not (participant.goal_1 or participant.goal_2 or participant.goal_3):
            continue

        GoalPeriod.objects.get_or_create(
            participant=participant,
            month=participant.goals_month,
            defaults={
                'goal_1': participant.goal_1 or "",
                'goal_2': participant.goal_2 or "",
                'goal_3': participant.goal_3 or "",
                'status': 'active',
            },
        )


def reverse_migrate(apps, schema_editor):
    # Откат миграции (если понадобится)
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('app_tracker', '0008_report_goal_1_note_report_goal_2_note_and_more'),
    ]

    operations = [
        migrations.RunPython(migrate_goals, reverse_migrate),
    ]
