from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need
# fine tuning.
build_options = {'packages': [], 'excludes': []}

base = 'gui'

executables = [
    Executable('test_scanner_gui.py', base=base, target_name = 'Scanner_App')
]

setup(name='SAR_Scanner',
      version = '1',
      description = 'Synthetic Aperture Radar Imager, Maintained by Flatrim Dreshaj.',
      options = {'build_exe': build_options},
      executables = executables)
