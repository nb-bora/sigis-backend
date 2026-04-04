"""Hachage des mots de passe (bcrypt) — instance unique partagée."""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
