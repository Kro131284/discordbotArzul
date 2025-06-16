# cogs/model/buttons_model.py

class RoleModel:
    """Verwaltet die Rollen-IDs."""

    ROLE_DATA = {
        "pve": {
            "tank": 1292512993099386890,
            "dps": 1292513076846919863,
            "healer": 1292513124787945482,
        },
        "pvp": {
            "pvp_tank": 1303033764477407282,
            "pvp_dps": 1303033919951601704,
            "pvp_healer": 1303034028135546930,
        },
    }

    @staticmethod
    def get_role_id(category, role_name):
        """Gibt die Rollen-ID für die angegebene Kategorie und den Rollennamen zurück."""
        category_data = RoleModel.ROLE_DATA.get(category)
        if category_data:
            return category_data.get(role_name)
        return None
