from brownie import Jumpgate, reverts
from utils.config import BRIDGE_DUST_CUTOFF
from utils.constants import one_quintillion
from utils.encode import get_address_encoder
import pytest


def test_deploy_parameters(token, bridge, owner, deploy_params):
    (recipientChain, recipient) = deploy_params

    # address encoding is different for different chains
    encode = get_address_encoder(recipientChain)
    recipient_encoded = encode(recipient)

    arbiter_fee = 0

    jumpgate = Jumpgate.deploy(
        owner.address,
        token.address,
        bridge.address,
        recipientChain,
        recipient_encoded,
        arbiter_fee,
        {"from": owner},
    )

    # check all deployment args
    assert jumpgate.owner() == owner.address
    assert jumpgate.token() == token.address
    assert jumpgate.bridge() == bridge.address
    assert jumpgate.recipientChain() == recipientChain
    assert jumpgate.recipient() == recipient_encoded
    assert jumpgate.arbiterFee() == arbiter_fee

    # make sure JumpgateCreated event fired
    assert "JumpgateCreated" in jumpgate.tx.events
    assert jumpgate.tx.events["JumpgateCreated"]["_token"] == token.address
    assert jumpgate.tx.events["JumpgateCreated"]["_bridge"] == bridge.address
    assert jumpgate.tx.events["JumpgateCreated"]["_recipientChain"] == recipientChain
    assert jumpgate.tx.events["JumpgateCreated"]["_recipient"] == recipient_encoded
    assert jumpgate.tx.events["JumpgateCreated"]["_arbiterFee"] == arbiter_fee


@pytest.mark.parametrize("amount", [0, 1, one_quintillion])
def test_recover_ether(
    jumpgate,
    destrudo,
    amount,
    sender,
    stranger,
):
    # remember jumpgate balance before sending ether to it
    jumpgate_balance_before = jumpgate.balance()

    # send ether to jumpgate by self-destrucing another contract
    destrudo.destructSelf(jumpgate.address, {"value": amount, "from": sender})

    # make sure jumpgate received ether
    assert jumpgate.balance() == jumpgate_balance_before + amount

    # remember jumpgate balance before recovery
    jumpgate_balance_before = jumpgate.balance()

    # recovering to stranger to avoid gas calculations
    recipient = stranger
    recipient_balance_before = recipient.balance()

    # recovery is owner-only
    is_owner = jumpgate.owner() == sender.address

    # recover as the owner
    if is_owner:
        tx = jumpgate.recoverEther(recipient.address, {"from": sender})

        assert recipient.balance() == jumpgate_balance_before + recipient_balance_before

        # make sure EtherRecovered is fired
        assert "EtherRecovered" in tx.events
        assert tx.events["EtherRecovered"]["_recipient"] == recipient.address
        assert tx.events["EtherRecovered"]["_amount"] == jumpgate_balance_before
    # attempt to recover as a non-owner
    else:
        with reverts("Ownable: caller is not the owner"):
            jumpgate.recoverEther(recipient.address, {"from": sender})


@pytest.mark.parametrize("amount", [0, 1, one_quintillion])
def test_recover_erc20(token, jumpgate, sender, token_holder, amount):
    # remember balances before token transfer
    holder_balance_before = token.balanceOf(token_holder.address)
    jumpgate_balance_before = token.balanceOf(jumpgate.address)

    # transfer tokens to jumpgate from holder
    token.transfer(jumpgate.address, amount, {"from": token_holder})

    # make sure tokens were transfered
    assert token.balanceOf(token_holder.address) == holder_balance_before - amount
    assert token.balanceOf(jumpgate.address) == jumpgate_balance_before + amount

    # remember balances before recovery
    holder_balance_before = token.balanceOf(token_holder.address)
    jumpgate_balance_before = token.balanceOf(jumpgate.address)

    # recovery is owner-only
    is_owner = jumpgate.owner() == sender.address

    # recover as the owner back to token holder
    if is_owner:
        tx = jumpgate.recoverERC20(
            token.address,
            token_holder.address,
            jumpgate_balance_before,
            {"from": sender},
        )

        # make sure token holder got back their tokens
        assert (
            token.balanceOf(token_holder.address)
            == holder_balance_before + jumpgate_balance_before
        )
        assert token.balanceOf(jumpgate.address) == 0

        # zero-token transfer do not fire Transfer event
        if amount > 0:
            assert "Transfer" in tx.events
            assert tx.events["Transfer"]["from"] == jumpgate.address
            assert tx.events["Transfer"]["to"] == token_holder.address
            assert tx.events["Transfer"]["value"] == jumpgate_balance_before

        # make sure the event fired
        assert "ERC20Recovered" in tx.events
        assert tx.events["ERC20Recovered"]["_token"] == token.address
        assert tx.events["ERC20Recovered"]["_recipient"] == token_holder.address
        assert tx.events["ERC20Recovered"]["_amount"] == jumpgate_balance_before
    # attempt to recover tokens as a non-owner
    else:
        with reverts("Ownable: caller is not the owner"):
            jumpgate.recoverERC20(
                token.address,
                token_holder.address,
                token.balanceOf(jumpgate.address),
                {"from": sender},
            )


def test_recover_erc721(jumpgate, sender, nft, nft_id, nft_holder):
    # make sure nft_holder still owns the nft
    assert nft.ownerOf(nft_id) == nft_holder

    # transfer the nft to jumpgate
    nft.transferFrom(nft_holder.address, jumpgate.address, nft_id, {"from": nft_holder})
    assert nft.ownerOf(nft_id) == jumpgate.address

    # recovery is owner-only
    is_owner = jumpgate.owner() == sender.address

    # recover as the owner
    if is_owner:
        # return nft back to original holder
        tx = jumpgate.recoverERC721(
            nft.address, nft_id, sender.address, {"from": sender}
        )

        assert nft.ownerOf(nft_id) == sender.address

        assert "Transfer" in tx.events
        assert tx.events["Transfer"]["from"] == jumpgate.address
        assert tx.events["Transfer"]["to"] == sender.address
        assert tx.events["Transfer"]["tokenId"] == nft_id

        # make sure ERC721Recovered event fired
        assert "ERC721Recovered" in tx.events
        assert tx.events["ERC721Recovered"]["_token"] == nft.address
        assert tx.events["ERC721Recovered"]["_tokenId"] == nft_id
        assert tx.events["ERC721Recovered"]["_recipient"] == sender.address
    # attempt to recover as a non-owner
    else:
        with reverts("Ownable: caller is not the owner"):
            jumpgate.recoverERC721(
                nft.address, nft_id, sender.address, {"from": sender}
            )


# cannot fully test recoverERC115 because jumpgate can't receive ERC1155
def test_send_erc1155_to_jumpgate(
    jumpgate, multitoken, multitoken_id, multitoken_holder
):
    # make sure multitoken_holder owns a multitoken
    assert multitoken.balanceOf(multitoken_holder.address, multitoken_id) == 1

    # try to transfer the token to jumpgate
    with reverts(""):
        multitoken.safeTransferFrom(
            multitoken_holder.address,
            jumpgate.address,
            multitoken_id,
            1,
            "",
            {"from": multitoken_holder},
        )


@pytest.mark.parametrize(
    "amount",
    [0, 1, BRIDGE_DUST_CUTOFF - 1, BRIDGE_DUST_CUTOFF, one_quintillion],
)
def test_bridge_tokens(jumpgate, token, amount, token_holder, bridge):
    # transfer tokens the jumpgate
    token.transfer(jumpgate.address, amount, {"from": token_holder})
    assert token.balanceOf(jumpgate.address) == amount

    bridge_balance_before = token.balanceOf(bridge.address)

    # bridgeTokens
    if amount < BRIDGE_DUST_CUTOFF:
        with reverts("Amount too small for bridging!"):
            jumpgate.bridgeTokens()
    else:
        tx = jumpgate.bridgeTokens()

        assert "Approval" in tx.events
        assert tx.events["Approval"]["owner"] == jumpgate.address
        assert tx.events["Approval"]["spender"] == bridge.address
        assert tx.events["Approval"]["value"] == amount

        assert "Transfer" in tx.events
        assert tx.events["Transfer"]["from"] == jumpgate.address
        assert tx.events["Transfer"]["to"] == bridge.address
        assert tx.events["Transfer"]["value"] == amount

        assert (
            token.balanceOf(jumpgate.address) == 0
            if amount >= BRIDGE_DUST_CUTOFF
            else amount
        )
        assert token.balanceOf(bridge.address) == bridge_balance_before + amount

        assert "LogMessagePublished" in tx.events
        assert tx.events["LogMessagePublished"]["sender"] == bridge.address
        assert tx.events["LogMessagePublished"]["sequence"] >= 0
        assert tx.events["LogMessagePublished"]["nonce"] == 0
        assert tx.events["LogMessagePublished"]["consistencyLevel"] == 15

        assert "TokensBridged" in tx.events
        assert tx.events["TokensBridged"]["_token"] == token.address
        assert tx.events["TokensBridged"]["_bridge"] == bridge.address
        assert (
            tx.events["TokensBridged"]["_recipientChain"] == jumpgate.recipientChain()
        )
        assert tx.events["TokensBridged"]["_recipient"] == jumpgate.recipient()
        assert tx.events["TokensBridged"]["_arbiterFee"] == jumpgate.arbiterFee()
        assert tx.events["TokensBridged"]["_amount"] == amount
        assert tx.events["TokensBridged"]["_nonce"] == 0
        assert (
            tx.events["TokensBridged"]["_transferSequence"]
            == tx.events["LogMessagePublished"]["sequence"]
        )
