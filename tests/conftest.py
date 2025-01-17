import pytest
from brownie import (
    Jumpgate,
    Destrudo,
    accounts,
    MockERC20,
    MockERC721,
    MockERC1155,
)
from utils.config import (
    ADD_REWARD_PROGRAM_EVM_SCRIPT_FACTORY,
    EASYTRACK,
    LDO,
    LDO_HOLDER,
    REWARD_PROGRAMS_REGISTRY,
    SOLANA_RANDOM_ADDRESS,
    SOLANA_WORMHOLE_CHAIN_ID,
    TERRA_RANDOM_ADDRESS,
    TERRA_WORMHOLE_CHAIN_ID,
    TOP_UP_REWARD_PROGRAM_EVM_SCRIPT_FACTORY,
    WORMHOLE_TOKEN_BRIDGE_ADDRESS,
)
from utils.contract import (
    init_add_reward_program_evm_script_factory,
    init_easytrack,
    init_ldo,
    init_reward_programs_registry,
    init_top_up_reward_program_evm_script_factory,
)
from utils.encode import encode_terra_address


@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


@pytest.fixture(scope="session")
def owner(accounts):
    return accounts[0]


@pytest.fixture(scope="session")
def non_owner(accounts):
    return accounts[1]


@pytest.fixture(scope="session")
def stranger(accounts):
    return accounts[2]


# test as the owner and a non-owner
@pytest.fixture(scope="session", params=["owner", "non_owner"])
def sender(request):
    return request.getfixturevalue(request.param)


@pytest.fixture(
    params=[
        (TERRA_WORMHOLE_CHAIN_ID, TERRA_RANDOM_ADDRESS),
        (SOLANA_WORMHOLE_CHAIN_ID, SOLANA_RANDOM_ADDRESS),
    ]
)
def deploy_params(request):
    return request.param


# ERC20
@pytest.fixture
def token_holder():
    return accounts.add()


@pytest.fixture
def token(token_holder):
    return MockERC20.deploy({"from": token_holder})


# ERC721
@pytest.fixture
def nft_holder(accounts):
    return accounts.add()


@pytest.fixture
def nft(nft_holder):
    return MockERC721.deploy({"from": nft_holder})


@pytest.fixture
def nft_id():
    return 0


# ERC1155
@pytest.fixture
def multitoken_holder(accounts):
    return accounts.add()


@pytest.fixture(scope="function")
def multitoken(multitoken_holder):
    return MockERC1155.deploy({"from": multitoken_holder})


@pytest.fixture
def multitoken_id():
    return 0


@pytest.fixture(scope="function")
def destrudo(owner):
    return Destrudo.deploy({"from": owner})


@pytest.fixture()
def jumpgate(owner, token, bridge):
    return Jumpgate.deploy(
        owner.address,
        token.address,
        bridge.address,
        TERRA_WORMHOLE_CHAIN_ID,
        encode_terra_address(TERRA_RANDOM_ADDRESS),
        0,
        {"from": owner},
    )


# Integrated tests


@pytest.fixture
def ldo_holder(accounts, chain):
    return accounts.at(LDO_HOLDER.get(chain.id), force=True)


@pytest.fixture
def ldo(chain):
    return init_ldo(LDO.get(chain.id))


@pytest.fixture()
def ldo_jumpgate(owner, ldo, bridge, chain):
    return Jumpgate.deploy(
        owner.address,
        ldo.address,
        bridge.address,
        TERRA_WORMHOLE_CHAIN_ID,
        encode_terra_address(TERRA_RANDOM_ADDRESS),
        0,
        {"from": owner},
    )


@pytest.fixture
def bridge(interface, chain):
    return interface.IWormholeTokenBridge(WORMHOLE_TOKEN_BRIDGE_ADDRESS.get(chain.id))


@pytest.fixture
def easytrack(chain):
    return init_easytrack(EASYTRACK.get(chain.id))


@pytest.fixture
def reward_programs_registry(chain):
    return init_reward_programs_registry(REWARD_PROGRAMS_REGISTRY.get(chain.id))


@pytest.fixture
def add_reward_program_evm_script_factory(chain):
    return init_add_reward_program_evm_script_factory(
        ADD_REWARD_PROGRAM_EVM_SCRIPT_FACTORY.get(chain.id)
    )


@pytest.fixture
def top_up_reward_program_evm_script_factory(chain):
    return init_top_up_reward_program_evm_script_factory(
        TOP_UP_REWARD_PROGRAM_EVM_SCRIPT_FACTORY.get(chain.id)
    )
