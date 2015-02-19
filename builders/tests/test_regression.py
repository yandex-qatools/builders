'This test implements a typical object set to have some regeression tests'
from builders.builder import Builder
from builders.construct import Uplink, Collection, Unique
from builders.model_graph import BuilderModelClass
from builders.modifiers import NumberOf, Given


class Unit(BuilderModelClass):
    name = ''
    type = ''
    squad = Uplink()


class Hero(BuilderModelClass):
    epic_name = ''
    squad = Uplink()


class Squad(BuilderModelClass):
    name = ''
    units = Collection(Unit)
    leader = Unique(Hero)
    player = Uplink()


class Player(BuilderModelClass):
    name = ''
    squads = Collection(Squad)


Unit.squad.linksTo(Squad, Squad.units)
Squad.player.linksTo(Player, Player.squads)
Hero.squad.linksTo(Squad, Squad.leader)


def test_create_default():
    p = Builder(Player).build()
    assert isinstance(p, Player)
    assert p.squads
    assert isinstance(p.squads[0], Squad)


def test_create_from_bottom():
    unit = Builder(Unit).build()
    assert isinstance(unit, Unit)
    assert isinstance(unit.squad, Squad)


def test_big_squads():
    player = Builder(Player).withA(NumberOf(Squad.units, 5)).build()
    assert len(player.squads[0].units) == 5


def test_lots_of_big_squads():
    player = Builder(Player).withA(NumberOf(Squad.units, 5), NumberOf(Player.squads, 3)).build()
    assert len(player.squads) == 3
    for squad in player.squads:
        assert isinstance(squad.leader, Hero)
        assert squad.leader.squad == squad
        assert len(squad.units) == 5


def test_player_created_for_unit():
    unit = Builder(Unit).build()
    assert isinstance(unit.squad.player, Player)


def test_two_separate_units():
    unit = Builder(Unit).build()
    unit2 = Builder(Unit).withA(Given(Unit.squad, unit.squad)).build()

    assert unit2.squad == unit.squad
