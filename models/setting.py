from extensions import db

class Setting(db.Model):
    __tablename__ = 'settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    value = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    @classmethod
    def get_value(cls, key, default=None):
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default

    @classmethod
    def get_int(cls, key, default=0):
        val = cls.get_value(key)
        try:
            return int(val) if val is not None else default
        except (ValueError, TypeError):
            return default

    @classmethod
    def get_float(cls, key, default=0.0):
        val = cls.get_value(key)
        try:
            return float(val) if val is not None else default
        except (ValueError, TypeError):
            return default

    @classmethod
    def set_value(cls, key, value, description=None):
        setting = cls.query.filter_by(key=key).first()
        if setting:
            setting.value = str(value)
            if description:
                setting.description = description
        else:
            setting = cls(key=key, value=str(value), description=description)
            db.session.add(setting)
        db.session.commit()
        return setting

    @classmethod
    def init_defaults(cls):
        """Seed default settings if not already present."""
        defaults = [
            ('library_name', 'Apex Smart Library & Analytics System', 'Official library portal name'),
            ('default_loan_days', '14', 'Standard borrowing duration in days'),
            ('fine_rate_per_day', '1.00', 'Late fine charged per day overdue'),
            ('max_books_per_member', '4', 'Maximum concurrent active loans per member'),
            ('currency_symbol', '$', 'Currency symbol used for fines and invoices')
        ]
        for key, val, desc in defaults:
            if not cls.query.filter_by(key=key).first():
                db.session.add(cls(key=key, value=val, description=desc))
        db.session.commit()

    def __repr__(self):
        return f'<Setting {self.key}={self.value}>'
