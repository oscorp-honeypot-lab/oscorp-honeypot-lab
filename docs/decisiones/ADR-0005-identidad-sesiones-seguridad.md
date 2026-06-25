# ADR-0005 - Identidad, sesiones y seguridad HTTP

Estado: aceptado.

Fecha: 25 de junio de 2026.

## Decisión

La aplicación utiliza sesiones opacas almacenadas en PostgreSQL. No se usan
JWT ni tokens en `localStorage`.

```text
contraseñas: Argon2id
roles: viewer, analyst, admin
sesión: token aleatorio de 256 bits
persistencia: solo SHA-256 del token
CSRF: token aleatorio asociado a la sesión
cookie de sesión: HttpOnly, SameSite=Lax
cookie Secure: obligatoria en REAL/producción
```

## Expiración

```text
absoluta: 8 horas
inactividad: 30 minutos
rotación: nuevo identificador en cada login
logout: revocación inmediata en PostgreSQL
```

## Controles HTTP

- CORS limitado por allowlist.
- CSRF de doble envío y validación contra la sesión persistida.
- Rate limit de login por usuario e IP.
- CSP, `frame-ancestors`, `nosniff`, `Referrer-Policy` y
  `Permissions-Policy`.
- Permisos comprobados en backend mediante jerarquía de roles.
- Auditoría de login, logout, expiración, creación de usuarios y bootstrap.

## Secretos

`setup.ps1` genera una contraseña administrativa aleatoria y estable dentro
del `.env` local ignorado por Git. El repositorio solo conserva el campo vacío
en `.env.example`.
