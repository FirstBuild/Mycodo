# coding=utf-8
#
# grove_pi_gpio.py - Output for simple GPIO switching of Grove Pi I/O
#
from flask import flash
from flask_babel import lazy_gettext

from mycodo.databases.models import OutputChannel
from mycodo.outputs.base_output import AbstractOutput
from mycodo.utils.database import db_retrieve_table_daemon


def execute_at_modification(
        mod_output,
        request_form,
        custom_options_dict_presave,
        custom_options_channels_dict_presave,
        custom_options_dict_postsave,
        custom_options_channels_dict_postsave):
    """
    This function allows you to view and modify the output and channel settings when the user clicks
    save on the user interface. Both the output and channel settings are passed to this function, as
    dictionaries. Additionally, both the pre-saved and post-saved options are available, as it's
    sometimes useful to know what settings changed and from what values. You can modify the post-saved
    options and these will be stored in the database.
    :param mod_output: The post-saved output database entry, minus the custom_options settings
    :param request_form: The requests.form object the user submitted
    :param custom_options_dict_presave: dict of pre-saved custom output options
    :param custom_options_channels_dict_presave: dict of pre-saved custom output channel options
    :param custom_options_dict_postsave: dict of post-saved custom output options
    :param custom_options_channels_dict_postsave: dict of post-saved custom output channel options
    :return:
    """
    allow_saving = True
    success = []
    error = []
    for each_error in error:
        flash(each_error, 'error')
    for each_success in success:
        flash(each_success, 'success')
    return (allow_saving,
            mod_output,
            custom_options_dict_postsave,
            custom_options_channels_dict_postsave)


def constraints_pass_positive_value(mod_dev, value):
    """
    Check if the user input is acceptable
    :param mod_dev: SQL object with user-saved Input options
    :param value: float or int
    :return: tuple: (bool, list of strings)
    """
    errors = []
    all_passed = True
    # Ensure value is positive
    if value <= 0:
        all_passed = False
        errors.append("Must be a positive value")
    return all_passed, errors, mod_dev


# Measurements
measurements_dict = {
    0: {
        'measurement': 'duration_time',
        'unit': 's'
    }
}

channels_dict = {
    0: {
        'types': ['on_off'],
        'measurements': [0]
    }
}

# Output information
OUTPUT_INFORMATION = {
    'output_name_unique': 'grove_pio_gpio',
    'output_name': "Grove Pi GPIO: {}".format(lazy_gettext('On/Off')),
    'output_library': 'smbus2',
    'measurements_dict': measurements_dict,
    'channels_dict': channels_dict,
    'execute_at_modification': execute_at_modification,
    'output_types': ['on_off'],

    'message': 'The specified GPIO pin will be set HIGH (3.3 volts) or LOW (0 volts) when turned '
               'on or off, depending on the On State option.',

    'options_enabled': [
        'button_on',
        'button_send_duration'
    ],
    'options_disabled': ['interface'],

    'dependencies_module': [
        ('pip-pypi', 'smbus2', 'smbus2')
    ],

    'interfaces': ['I2C'],
    'i2c_location': [
        '0x04'
    ],
    'i2c_address_editable': False,
    'i2c_address_default': '0x04',

    'custom_channel_options': [
        {
            'id': 'pin',
            'type': 'select',
            'default_value': 2,
            'required': True,
            'options_select': [
                (2, 'D2'),
                (3, 'D3'),
                (4, 'D4'),
                (5, 'D5'),
                (6, 'D6'),
                (7, 'D7'),
                (8, 'D8'),
                (14, 'A0'),
                (15, 'A1'),
                (16, 'A1')
            ],
            'name': lazy_gettext('Grove Pi Pin'),
            'phrase': lazy_gettext('The pin to control the state of')
        },
        {
            'id': 'state_startup',
            'type': 'select',
            'default_value': 0,
            'options_select': [
                (0, 'Off'),
                (1, 'On')
            ],
            'name': lazy_gettext('Startup State'),
            'phrase': lazy_gettext('Set the state when Mycodo starts')
        },
        {
            'id': 'state_shutdown',
            'type': 'select',
            'default_value': 0,
            'options_select': [
                (0, 'Off'),
                (1, 'On')
            ],
            'name': lazy_gettext('Shutdown State'),
            'phrase': lazy_gettext('Set the state when Mycodo shuts down')
        },
        {
            'id': 'on_state',
            'type': 'select',
            'default_value': 1,
            'options_select': [
                (1, 'HIGH'),
                (0, 'LOW')
            ],
            'name': lazy_gettext('On State'),
            'phrase': lazy_gettext('The state of the GPIO that corresponds to an On state')
        },
        {
            'id': 'trigger_functions_startup',
            'type': 'bool',
            'default_value': False,
            'name': lazy_gettext('Trigger Functions at Startup'),
            'phrase': lazy_gettext('Whether to trigger functions when the output switches at startup')
        },
        {
            'id': 'amps',
            'type': 'float',
            'default_value': 0.0,
            'required': True,
            'name': lazy_gettext('Current (Amps)'),
            'phrase': lazy_gettext('The current draw of the device being controlled')
        }
    ]
}


class OutputModule(AbstractOutput):
    """
    An output support class that operates an output
    """
    def __init__(self, output, testing=False):
        super(OutputModule, self).__init__(output, testing=testing, name=__name__)

        self.bus = None
        self.address = 0x04

        output_channels = db_retrieve_table_daemon(
            OutputChannel).filter(OutputChannel.output_id == self.output.unique_id).all()
        self.options_channels = self.setup_custom_channel_options_json(
            OUTPUT_INFORMATION['custom_channel_options'], output_channels)

    def setup_output(self):
        from smbus2 import SMBus

        self.setup_on_off_output(OUTPUT_INFORMATION)

        try:
            self.address = int(str(self.output.i2c_location), 16)
            self.bus = SMBus(self.output.i2c_bus)
            if self.options_channels['state_shutdown'][0] == 1:
                self.shutdown_state = 'on'
            else:
                self.shutdown_state = 'off'


        except Exception as except_msg:
            self.logger.exception("Cannot open i2c port")
            return

        self.logger.debug("I2C: Address: {}, Bus: {}, Port: {}".format(
            self.output.i2c_location, 
            self.output.i2c_bus,
            self.options_channels['pin'][0]))

        if self.options_channels['pin'][0] is None:
            self.logger.error("Pin must be set")
        else:

            try:
                if self.options_channels['state_startup'][0]:
                    startup_state = self.options_channels['on_state'][0]
                else:
                    startup_state = not self.options_channels['on_state'][0]

                self.output_setup = True
                self.bus.write_i2c_block_data(self.address, 5, 
                                [self.options_channels['pin'][0], 
                                 1,
                                0])
                self.output_switch(startup_state)

                if self.options_channels['trigger_functions_startup'][0]:
                    self.check_triggers(self.unique_id, output_channel=0)

                startup = 'ON' if self.options_channels['state_startup'][0] else 'OFF'
                state = 'HIGH' if self.options_channels['on_state'][0] else 'LOW'
                self.logger.info(
                    "Output setup on pin {pin} and turned {startup} (ON={state})".format(
                        pin=self.options_channels['pin'][0], startup=startup, state=state))
            except Exception as except_msg:
                self.logger.exception(
                    "Output was unable to be setup on pin {pin} with trigger={trigger}: {err}".format(
                        pin=self.options_channels['pin'][0],
                        trigger=self.options_channels['on_state'][0],
                        err=except_msg))

    def output_switch(self, state, output_type=None, amount=None, output_channel=0):
        try:
            if state == 'on':
                self.bus.write_i2c_block_data(self.address, 2, 
                                [self.options_channels['pin'][output_channel], 
                                 self.options_channels['on_state'][output_channel],
                                0])
            elif state == 'off':
                self.bus.write_i2c_block_data(self.address, 2,
                                [self.options_channels['pin'][output_channel],
                                 not self.options_channels['on_state'][output_channel],
                                 0])
            msg = "success"
        except Exception as e:
            msg = "State change error: {}".format(e)
            self.logger.exception(msg)
        return msg

    def is_on(self, output_channel=0):
        if self.is_setup():
            try:
                self.bus.write_i2c_block_data(self.address, 1,
                                [self.options_channels['pin'][output_channel], 0, 0])
                value = self.bus.read_i2c_block_data(self.address, 1, 2)
                return self.options_channels['on_state'][output_channel] == value[1]
            except Exception as e:
                self.logger.error("Status check error: {}".format(e))

    def is_setup(self):
        return self.output_setup

    def stop_output(self):
        """ Called when Output is stopped """
        if self.options_channels['state_shutdown'][0] == 1:
            self.output_switch('on', output_channel=0)
        elif self.options_channels['state_shutdown'][0] == 0:
            self.output_switch('off', output_channel=0)
        self.running = False
