import os
os.chdir(r'C:\Users\HomePC\Desktop\PROJECT WORK\iot_portal')
import sys
sys.path.insert(0, r'C:\Users\HomePC\Desktop\PROJECT WORK\iot_portal')
import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'iot_portal.settings'
django.setup()

from catalogue.templatetags.map_extras import dataset_tags, quality_stars, date_range
from catalogue.models import Dataset

d = Dataset.objects.first()
with open(r'C:\Users\HomePC\AppData\Local\Temp\kilo\filter_test2.txt', 'w', encoding='utf-8') as f:
    f.write('Tags: ' + ', '.join(dataset_tags(d)) + '\n')
    f.write('Stars: ' + quality_stars(d.quality_score) + '\n')
    f.write('Date range: ' + date_range(d) + '\n')
