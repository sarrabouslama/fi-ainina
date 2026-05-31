from enum import Enum


class UserRole(str, Enum):
    caregiver = 'caregiver'
    elderly = 'elderly'
    admin = 'admin'