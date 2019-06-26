"""
**Copyright**::

    +===================================================+
    |                 © 2019 Privex Inc.                |
    |               https://www.privex.io               |
    +===================================================+
    |                                                   |
    |        CryptoToken Converter                      |
    |                                                   |
    |        Core Developer(s):                         |
    |                                                   |
    |          (+)  Chris (@someguy123) [Privex]        |
    |                                                   |
    +===================================================+

"""
import logging
#import privex.steemengine.exceptions as SENG
from typing import List, Tuple
#from beem.exceptions import MissingKeyError
from decimal import Decimal, getcontext, ROUND_DOWN
from payments.coin_handlers.base import exceptions, BaseManager
from payments.coin_handlers.Bitshares.BitsharesMixin import BitsharesMixin
from django.conf import settings
#from privex.steemengine import SteemEngineToken
#from steemengine.helpers import empty

from bitshares.account import Account
from bitshares.amount import Amount

getcontext().rounding = ROUND_DOWN


log = logging.getLogger(__name__)


class BitsharesManager(BaseManager, BitsharesMixin):
    """
    This class handles various operations for the **Bitshares* network, and supports almost any token
    on Bitshares.

    It handles:

    - Validating source/destination accounts
    - Checking the balance for a given account, as well as the total amount received with a certain ``memo``
    - Issuing tokens to users
    - Sending tokens to users

    **Copyright**::

        +===================================================+
        |                 © 2019 Privex Inc.                |
        |               https://www.privex.io               |
        +===================================================+
        |                                                   |
        |        CryptoToken Converter                      |
        |                                                   |
        |        Core Developer(s):                         |
        |                                                   |
        |          (+)  Chris (@someguy123) [Privex]        |
        |                                                   |
        +===================================================+

    """

    provides = []  # type: List[str]
    """
    This attribute is automatically generated by scanning for :class:`models.Coin` s with the type ``bitshares``. 
    This saves us from hard coding specific coin symbols. See __init__.py for populating code.
    """

    def __init__(self, symbol: str):
        super().__init__(symbol.upper())

    def health(self) -> Tuple[str, tuple, tuple]:
        """
        Return health data for the passed symbol.

        Health data will include: symbol, status, API node, symbol issuer, symbol precision,
        our account for transacting with this symbol, and our account's balance of this symbol

        :return tuple health_data: (manager_name:str, headings:list/tuple, health_data:list/tuple,)
        """
        headers = ('Symbol', 'Status', 'API Node', 'Issuer',
                   'Precision', 'Our Account', 'Our Balance')

        class_name = type(self).__name__
        balance_str = '<b style="color: red">{}</b>'.format("ERROR GETTING BALANCE")
        precision_str = '<b style="color: red">{}</b>'.format("ERROR GETTING PRECISION")
        issuer = '<b style="color: red">{}</b>'.format("ERROR GETTING ISSUER")
        our_account_name = '<b style="color: red">{}</b>'.format("ERROR GETTING ACCOUNT NAME")

        status = 'Okay'
        try:
            our_asset = self.get_asset_obj(self.symbol)
            if our_asset is None:
                precision_str = '<b style="color: red">{}</b>'.format('Symbol %s not found' % (self.symbol,))
                issuer = precision_str
                status = 'ERROR'
            else:
                precision_str = str(our_asset["precision"])
                issuer_obj = self.get_account_obj(our_asset["issuer"])
                if issuer_obj is None:
                    issuer = our_asset["issuer"]
                else:
                    issuer = issuer_obj.name

            our_account = self.get_account_obj(self.coin.our_account)
            if our_account is None:
                our_account_name = '<b style="color: red">{}</b>'.format('Account %s not found' % (self.coin.our_account,))
                status = 'ERROR'
            else:
                our_account_name = our_account.name
                if our_asset is None:
                    balance_str = '0.0'
                else:
                    amount_obj = our_account.balance(self.symbol)
                    raw_amount = Decimal(int(amount_obj))
                    balance = raw_amount / (10 ** amount_obj.asset["precision"])
                    balance_str = ('{0:,.' + str(amount_obj.asset["precision"]) + 'f}').format(balance)
        except:
            status = 'UNHANDLED EXCEPTION (see logs)'
            log.exception('Exception during %s.health for symbol %s', class_name, self.symbol)

        if status == 'Okay':
            status = '<b style="color: green">{}</b>'.format(status)
        else:
            status = '<b style="color: red">{}</b>'.format(status)

        data = (self.symbol, status, settings.BITSHARES_RPC_NODE, issuer, precision_str, our_account_name, balance_str)
        return class_name, headers, data

    def health_test(self) -> bool:
        """
        Check if the Bitshares API and node connection works or not, by requesting basic information such as
        the token metadata, and checking if our sending/receiving account exists.

        :return bool: True if Bitshares appears to be working, False if broken.
        """
        try:
            _, _, health_data = self.health()
            if 'Okay' in health_data[1]:
                return True
            return False
        except:
            return False

    def balance(self, address: str = None, memo: str = None, memo_case: bool = False) -> Decimal:
        """
        Get token balance for a given Bitshares account, if memo is given - get total symbol amt received with this memo.

        :param address:    Bitshares account to get balance for, if not set, uses self.coin.our_account
        :param memo:       If not None, get total `self.symbol` received with this memo.
        :param memo_case:  Case sensitive memo search
        :return: Decimal(balance)
        """
        bal = Decimal(0)
        #if address is None:
        #    address = self.coin.our_account
        #address = address.lower()
        #if memo is not None:
        #    memo = str(memo).strip()
        #if empty(memo):
        #    return self.eng_rpc.get_token_balance(user=address, symbol=self.symbol)
        #txs = self.eng_rpc.list_transactions(user=address, symbol=self.symbol, limit=1000)
        #bal = Decimal(0)
        #for t in txs:
        #    if t['to'] == address and t['symbol'] == self.symbol:
        #        m = t['memo'].strip()
        #        if m == memo or (not memo_case and m == memo.lower()):
        #            bal += Decimal(t['quantity'])
        return bal

    def get_deposit(self) -> tuple:
        """
        Returns the deposit account for this symbol

        :return tuple: A tuple containing ('account', receiving_account). The memo must be generated
                       by the calling function.
        """

        return 'account', self.coin.our_account

    def address_valid(self, address) -> bool:
        """If an account ( ``address`` param) exists on Bitshares, will return True. Otherwise False."""
        isSuccess = True

        #try:
        #    return self.eng_rpc.account_exists(address)
        #except:
        #    log.exception('Something went wrong while running %s.address_valid. Returning NOT VALID.', type(self))
        #    return False
        return isSuccess

    def issue(self, amount: Decimal, address: str, memo: str = None) -> dict:
        """
        Issue (create/print) tokens to a given address/account, optionally specifying a memo if supported

        Example - Issue 5.10 BUILDTEAM to @privex

            >>> s = BitsharesManager('BUILDTEAM')
            >>> s.issue(address='privex', amount=Decimal('5.10'))

        :param Decimal amount:      Amount of tokens to issue, as a Decimal()
        :param address:             Address or account to issue the tokens to
        :param memo:                (ignored) Cannot issue tokens with a memo on Bitshares   TODO: I don't think this is true, need to add support for this
        :raises IssuerKeyError:     Cannot issue because we don't have authority to (missing key etc.)
        :raises IssueNotSupported:  Class does not support issuing, or requested symbol cannot be issued.
        :raises AccountNotFound:    The requested account/address doesn't exist
        :return dict: Result Information

        Format::

          {
              txid:str - Transaction ID - None if not known,
              coin:str - Symbol that was sent,
              amount:Decimal - The amount that was sent (after fees),
              fee:Decimal    - TX Fee that was taken from the amount,
              from:str       - The account/address the coins were issued from,
              send_type:str       - Should be statically set to "issue"
          }

        """
        raise exceptions.IssueNotSupported("{} does not support issuing tokens.".format(type(self).__name__))

        #try:
        #    token = self.eng_rpc.get_token(symbol=self.symbol)

            # If we get passed a float for some reason, make sure we trim it to the token's precision before
            # converting it to a Decimal.
        #    if type(amount) == float:
        #        amount = ('{0:.' + str(token['precision']) + 'f}').format(amount)
        #    amount = Decimal(amount)
        #    issuer = self.eng_rpc.get_token(self.symbol)['issuer']
        #    log.debug('Issuing %f %s to @%s', amount, self.symbol, address)
        #    t = self.eng_rpc.issue_token(symbol=self.symbol, to=address, amount=amount)
        #    txid = None     # There's a risk we can't get the TXID, and so we fall back to None.
        #    if 'transaction_id' in t:
        #        txid = t['transaction_id']
        #    return {
        #        'txid': txid,
        #        'coin': self.symbol,
        #        'amount': amount,
        #        'fee': Decimal(0),
        #        'from': issuer,
        #        'send_type': 'issue'
        #    }
        #except SENG.AccountNotFound as e:
        #    raise exceptions.AccountNotFound(str(e))
        #except MissingKeyError:
        #    raise exceptions.IssuerKeyError('Missing active key for issuer account {}'.format(issuer))

    def send(self, amount, address, memo=None, from_address=None) -> dict:
        """
        Send tokens to a given address/account, optionally specifying a memo if supported

        Example - send 1.23 BUILDTEAM from @someguy123 to @privex with memo 'hello'

            >>> s = BitsharesManager('BUILDTEAM')
            >>> s.send(from_address='someguy123', address='privex', amount=Decimal('1.23'), memo='hello')

        :param Decimal amount:      Amount of tokens to send, as a Decimal()
        :param address:             Account to send the tokens to
        :param from_address:        Account to send the tokens from
        :param memo:                Memo to send tokens with (if supported)
        :raises AttributeError:     When both `from_address` and `self.coin.our_account` are blank.
        :raises ArithmeticError:    When the amount is lower than the lowest amount allowed by the token's precision
        :raises AuthorityMissing:   Cannot send because we don't have authority to (missing key etc.)
        :raises AccountNotFound:    The requested account/address doesn't exist
        :raises TokenNotFound:      When the requested token `symbol` does not exist
        :raises NotEnoughBalance:   The account `from_address` does not have enough balance to send this amount.
        :return dict: Result Information

        Format::

          {
              txid:str - Transaction ID - None if not known,
              coin:str - Symbol that was sent,
              amount:Decimal - The amount that was sent (after fees),
              fee:Decimal    - TX Fee that was taken from the amount,
              from:str       - The account/address the coins were sent from,
              send_type:str       - Should be statically set to "send"
          }

        """
        raise NotImplemented("{}.send must be implemented!".format(type(self).__name__))
        # Try from_address first. If that's empty, try using self.coin.our_account. If both are empty, abort.
        #if empty(from_address):
        #    if empty(self.coin.our_account):
        #        raise AttributeError("Both 'from_address' and 'coin.our_account' are empty. Cannot send.")
        #    from_address = self.coin.our_account
        #try:
        #    token = self.eng_rpc.get_token(symbol=self.symbol)

            # If we get passed a float for some reason, make sure we trim it to the token's precision before
            # converting it to a Decimal.
        #    if type(amount) == float:
        #        amount = ('{0:.' + str(token['precision']) + 'f}').format(amount)
        #    amount = Decimal(amount)

        #    log.debug('Sending %f %s to @%s', amount, self.symbol, address)

        #    t = self.eng_rpc.send_token(symbol=self.symbol, from_acc=from_address,
        #                                to_acc=address, amount=amount, memo=memo)
        #    txid = None  # There's a risk we can't get the TXID, and so we fall back to None.
        #    if 'transaction_id' in t:
        #        txid = t['transaction_id']
        #    return {
        #        'txid': txid,
        #        'coin': self.symbol,
        #        'amount': amount,
        #        'fee': Decimal(0),
        #        'from': from_address,
        #        'send_type': 'send'
        #    }
        #except SENG.AccountNotFound as e:
        #    raise exceptions.AccountNotFound(str(e))
        #except SENG.TokenNotFound as e:
        #    raise exceptions.TokenNotFound(str(e))
        #except SENG.NotEnoughBalance as e:
        #    raise exceptions.NotEnoughBalance(str(e))
        #except MissingKeyError:
        #    raise exceptions.AuthorityMissing('Missing active key for sending account {}'.format(from_address))

    def send_or_issue(self, amount, address, memo=None) -> dict:
        try:
            log.debug(f'Attempting to send {amount} {self.symbol} to {address} ...')
            return self.send(amount=amount, address=address, memo=memo)
        except Exception as e:
            log.debug(f'Got exception {e}')
        #except exceptions.NotEnoughBalance:
        #    acc = self.coin.our_account
        #    log.debug(f'Not enough balance. Issuing {amount} {self.symbol} to our account {acc} ...')

            # Issue the coins to our own account, and then send them. This prevents problems caused when issuing
            # directly to third parties.
        #    self.issue(amount=amount, address=acc, memo=f"Issuing to self before transfer to {address}")

        #    log.debug(f'Sending newly issued coins: {amount} {self.symbol} to {address} ...')
        #    tx = self.send(amount=amount, address=address, memo=memo, from_address=acc)
            # So the calling function knows we had to issue these coins, we change the send_type back to 'issue'
        #    tx['send_type'] = 'issue'
        #    return tx
