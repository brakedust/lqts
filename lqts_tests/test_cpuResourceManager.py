from lqts.resources import CPUResourceManager, CPUResponse


def test_manager():

    crm = CPUResourceManager(10)

    assert crm.cpu_count == 10

    response = crm.get_processors(count=1)
    success, cpus = response

    assert success
    assert len(cpus) == 1
    assert 2 in cpus

    assert 9 == crm.cpu_avalaible_count()

    crm.free_processors(cpus)

    assert 10 == crm.cpu_avalaible_count()


def test_manager_use_all():

    crm = CPUResourceManager(10)

    success, cpus1 = crm.get_processors(count=4)
    assert success
    assert len(cpus1) == 4

    assert 6 == crm.cpu_avalaible_count()

    success, cpus2 = crm.get_processors(count=4)
    assert success
    assert len(cpus2) == 4

    assert 2 == crm.cpu_avalaible_count()

    success, cpus3 = crm.get_processors(count=4)
    assert not success
    assert len(cpus3) == 0
    assert 2 == crm.cpu_avalaible_count()

    crm.free_processors(cpus1)
    crm.free_processors(cpus3)

    success, cpus3 = crm.get_processors(count=4)
    assert success
    assert len(cpus3) == 4

