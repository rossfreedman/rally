from app.models.database_models import Player, UserPlayerAssociation


# Helper functions for UserPlayerAssociation operations with normalized schema
def find_user_player_association(db_session, user_id, player_record):
    """Find association using the normalized schema"""
    return (
        db_session.query(UserPlayerAssociation)
        .filter(
            UserPlayerAssociation.user_id == user_id,
            UserPlayerAssociation.tenniscores_player_id
            == player_record.tenniscores_player_id,
        )
        .first()
    )


def create_user_player_association(user_id, player_record, is_primary=False):
    """Create association using the normalized schema"""
    return UserPlayerAssociation(
        user_id=user_id,
        tenniscores_player_id=player_record.tenniscores_player_id,
        is_primary=is_primary,
    )


def get_user_associated_players(db_session, user_id):
    """Get all players associated with a user using the normalized schema"""
    associations = (
        db_session.query(UserPlayerAssociation)
        .filter(UserPlayerAssociation.user_id == user_id)
        .all()
    )

    players = []
    for assoc in associations:
        player = assoc.get_player(db_session)
        if player:
            players.append(player)

    return players
