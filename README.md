# Install
### Install env

```bash
  python3 -m venv venv
```

### Windows activate env
```bash
    ./venv/Scripts/activate
```

### Linux activate env
```bash
    source ./venv/bin/activate
```

### Install requirements lib
```bash
    pip install -r requirements.txt
```

### Create .env file
```commandline
    copy .flashenv.sample .flaskenv
```

# Run

```bash
    flask run
```

# Create new user

Открываем консоль
```bash
    flask shell
```

```python
    db.create_all()
    u = User()
    u.username
    u.username = 'Admin'
    u.set_password('Admin')
    db.session.commit()
```