from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0004_dataset_extended_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dataset',
            name='domain',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='datasets', to='catalogue.domain'),
        ),
    ]
