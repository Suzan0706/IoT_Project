from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0003_profile'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='dataset',
            name='domain',
        ),
        migrations.RenameField(
            model_name='dataset',
            old_name='sampling_interval',
            new_name='update_frequency',
        ),
        migrations.AlterField(
            model_name='dataset',
            name='end_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='dataset',
            name='department',
            field=models.CharField(default='ICT', max_length=100),
        ),
        migrations.AddField(
            model_name='dataset',
            name='download_link',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='dataset',
            name='domain',
            field=models.CharField(choices=[('Transport', 'Transport'), ('Housing', 'Housing'), ('Heritage', 'Heritage'), ('Energy', 'Energy'), ('Water', 'Water'), ('Air Quality', 'Air Quality'), ('Agriculture', 'Agriculture'), ('Health', 'Health')], max_length=100),
        ),
        migrations.AddField(
            model_name='dataset',
            name='iuc_project_code',
            field=models.CharField(max_length=100),
        ),
        migrations.AddField(
            model_name='dataset',
            name='license',
            field=models.CharField(choices=[('CC BY 4.0', 'CC BY 4.0'), ('CC0', 'CC0'), ('CC BY-SA 4.0', 'CC BY-SA 4.0'), ('MIT', 'MIT'), ('Other', 'Other')], default='CC BY 4.0', max_length=100),
        ),
        migrations.AddField(
            model_name='dataset',
            name='output_format',
            field=models.CharField(choices=[('CSV', 'CSV'), ('JSON', 'JSON'), ('Parquet', 'Parquet'), ('XML', 'XML'), ('Other', 'Other')], default='CSV', max_length=20),
        ),
        migrations.AddField(
            model_name='dataset',
            name='sensor_type',
            field=models.CharField(choices=[('Temperature', 'Temperature'), ('Humidity', 'Humidity'), ('Air Quality', 'Air Quality'), ('Water Quality', 'Water Quality'), ('Energy', 'Energy'), ('Motion', 'Motion'), ('Sound', 'Sound'), ('Light', 'Light'), ('Other', 'Other')], default='Other', max_length=100),
        ),
        migrations.AddField(
            model_name='dataset',
            name='units_of_measurement',
            field=models.CharField(max_length=100),
        ),
    ]
