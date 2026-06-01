# orion
![ORION Startup Screen](./misc/orion.png)

## Documentation

### Config file
Inside the `conf/` directory copy the `config.json.default` to `config.json`. By default the application is looking for this file to load up settings. Once you made a copy, open the file in your favorite text-based editor (e.g. `nano config.json`) and make your changes. At minimum you have to adjust your location by entering latitude and longitude in decimal format.

- latitude - The latitude of your ORION box (decimal)
- longitude - The longitude of you ORION box (decimal)
- temp_image_dir - Location of the temporarily (nightly) captured images which are later merged together (string)
- final_image_dir - Location where the final merged image should be saved (string)
- imaging_interval - Frequency of capturing images in seconds (int)
- camera_shutter - For how long should the camera be capturing the open sky in microseconds (int)
- log_to_file - Write status and error messages into a log file, not just the screen (bool)


### Switches
Script `orion.py` accept several command line arguments which overwrite certain default behaviors.

- -c or --config <file> - Supply alternate path to the JSON config file
- -no_splash - Do not show the start up screen


## Requirements
### Python
!INCLUDE "requirements.txt"

### Prototype
- [x] SBC [Pi 0 2W, 4, 5]
- [ ] GPS coords [4G/LTE hat]
- [x] Cell modem [4G/LTE hat]
- [x] servo iris control [Pi GPIO/PWM]
- [x] image acquisition [Pi camera module]
- [x] stacking [software]
- [ ] object/line detection [software]
- [ ] solar power input [charge controller]
- [ ] run on battery power [charge controller + 5000mAh LiPo]
- [ ] PoE input [hat]
- [ ] enclosure
- [ ] glass cover
- [x] led indicator
