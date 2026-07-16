from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sources', '0002_streamingnode_streamingsetting'),
    ]

    operations = [
        migrations.AddField(
            model_name='streamingsetting',
            name='mediamtx_playback_url',
            field=models.CharField(
                default='http://127.0.0.1:9996',
                max_length=255,
                verbose_name='MediaMTX Playback URL'
            ),
        ),
        migrations.AddField(
            model_name='streamingsetting',
            name='dvr_buffer_minutes',
            field=models.IntegerField(
                default=10,
                help_text='Rolling DVR buffer duration in minutes. Default: 10 min. Max: 30 min.',
                verbose_name='DVR Buffer (minutes)'
            ),
        ),
    ]
