'''
Tests for specific :py:class:`builders.construct.Construct`-s

Created on Apr 12, 2013

@author: pupssman
'''
from builders.builder import Builder
from builders.construct import Random, Uid, Key, Lambda
from builders.model_graph import BuilderModelClass
import pytest


@pytest.mark.parametrize('run', range(100))
def test_random_number(run):
    class A(BuilderModelClass):
        a = Random(1, 10)

    value = Builder(A).build()

    assert value.a >= 1
    assert value.a <= 10


@pytest.mark.parametrize('run', range(100))
def test_random_string(run):
    class A(BuilderModelClass):
        a = Random(1, 10, 'foo_%s')

    value = Builder(A).build().a

    assert value[:4] == 'foo_'
    assert int(value[4:]) >= 1
    assert int(value[4:]) <= 10


def test_uid_gives_valid_uid():
    class A(BuilderModelClass):
        a = Uid()

    value = Builder(A).build().a

    import uuid
    uuid.UUID(value)


def test_uid_is_random():
    class A(BuilderModelClass):
        a = Uid()

    values = [Builder(A).build().a for _ in xrange(100)]

    assert sorted(list(set(values))) == sorted(values)


def test_key_is_unique():
    class A(BuilderModelClass):
        a = Key(Random(start=1, end=100))

    values = [Builder(A).build().a for _ in xrange(100)]

    assert sorted(list(set(values))) == sorted(values)


def test_lambda_executed_twice():
    from itertools import count
    gen = count()

    class A(BuilderModelClass):
        a = Lambda(lambda _: gen.next())

    values = [Builder(A).build().a for _ in xrange(2)]

    assert (values[0], values[1]) == (0, 1)


def test_class_passed_to_lambda():
    def check_instance_passed(instance):
        assert isinstance(instance, A)

    class A(BuilderModelClass):
        a = Lambda(check_instance_passed)

    Builder(A).build()
