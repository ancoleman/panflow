# dmg_config.py
# Configuration for dmgbuild

app = '/Users/antoncoleman/Documents/repos/fix/panflow/dist/PANFlow.app'
appname = 'PANFlow'
format = 'UDBZ'
size = '500M'
files = [
    '/Users/antoncoleman/Documents/repos/fix/panflow/dist/PANFlow.app',
]
symlinks = {
    'Applications': '/Applications',
}
badge_icon = None
background = None
icon_locations = {
    'PANFlow.app': (140, 120),
    'Applications': (500, 120),
}
window_rect = ((100, 100), (640, 280))
default_view = 'icon-view'
show_icon_preview = False
include_icon_view_settings = True
include_list_view_settings = False
arrange_by = None
grid_offset = (0, 0)
grid_spacing = 100
scroll_position = (0, 0)
label_pos = 'bottom'
text_size = 16
icon_size = 128
