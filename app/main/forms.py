from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField
from wtforms.validators import ValidationError, InputRequired, DataRequired, NumberRange


class SearchPredictForm(FlaskForm):
    analysis_number = StringField('Введите номер исследования', [InputRequired()])
    submit = SubmitField('Поиск')

    # def validate_search(form, field):
    #     if not field.dataget('analysis_number').isdigit():
    #         raise ValidationError('Номер исследования это целое число')


class SettingsForm(FlaskForm):
    """
        Цвет контура
        Цвет надписи
        процент фильтра белого
        процент фильра черного
    """
    color_box_R = IntegerField('Цвет контура R', validators=[NumberRange(min=0, max=255, message='0-255')])
    color_box_G = IntegerField('Цвет контура G', validators=[NumberRange(min=0, max=255, message='0-255')])
    color_box_B = IntegerField('Цвет контура B', validators=[NumberRange(min=0, max=255, message='0-255')])

    color_name_R = IntegerField('Цвет надписи R', validators=[NumberRange(min=0, max=255, message='0-255')])
    color_name_G = IntegerField('Цвет надписи G', validators=[NumberRange(min=0, max=255, message='0-255')])
    color_name_B = IntegerField('Цвет надписи B', validators=[NumberRange(min=0, max=255, message='0-255')])

    percentage_white = IntegerField('Максимальный процент белого на избражении',
                                    validators=[NumberRange(min=0, max=100, message='0-100%')])
    percentage_black = IntegerField('Максимальный процент черного на избражении',
                                    validators=[NumberRange(min=0, max=100, message='0-100%')])

    submit = SubmitField('Изменить настройки')
    default = SubmitField('Настройки по умолчанию')
