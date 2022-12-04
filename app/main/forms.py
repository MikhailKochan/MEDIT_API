from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import ValidationError, InputRequired


class SearchPredictForm(FlaskForm):
    analysis_number = StringField('Введите номер исследования', [InputRequired()])
    submit = SubmitField('Поиск')

    def validate_search(form, field):
        if not field.data.isdigit():
            raise ValidationError('Номер исследования это целое число')
