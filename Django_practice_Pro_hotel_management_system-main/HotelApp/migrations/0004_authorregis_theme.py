from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('HotelApp', '0003_alter_authorregis_managers'),
    ]

    operations = [
        migrations.AddField(
            model_name='authorregis',
            name='theme',
            field=models.CharField(choices=[('light', 'Light'), ('dark', 'Dark')], default='light', max_length=10),
        ),
    ]
