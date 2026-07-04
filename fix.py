with open('app.py', 'r') as f:
    content = f.read()

content = content.replace(
    'generate_password_hash("change-this-password")',
    'generate_password_hash("change-this-password", method="pbkdf2:sha256")'
)

with open('app.py', 'w') as f:
    f.write(content)

print('Fixed!')