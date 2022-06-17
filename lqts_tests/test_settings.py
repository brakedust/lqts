import os
os.environ['LQTS_PORT'] = "9300"

import lqts.config
from importlib import reload


def test_port():

    # c = lqts.config.Configuration()
    # assert c.port == 9200

    print(os.environ.get('LQTS_PORT', None))
    reload(lqts.config)
    os.environ['LQTS_PORT'] = "9300"
    print(os.environ['LQTS_PORT'])
    c = lqts.config.Configuration()
    print(c.port)
    assert c.port == 9300



if __name__ == "__main__":
    test_port()