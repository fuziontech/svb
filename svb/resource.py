import urllib
import warnings
import sys
from copy import deepcopy

from svb import api_requestor, error, util, upload_api_base
from svb.six import iteritems, string_types

def convert_to_svb_object(resp, api_key, account):
    types = {
        'account': Account,
        'ach': ACH,
        'book': Book,
        'virtualcard': VirtualCard,
        'wire': Wire,
        'company': Company,
        'person': Person,
        'file_upload': FileUpload,
        'login': Login,
        'parent_company': ParentCompany,
        'address': Address,
        'document': Document,
        'gov_ident': GovernmentID,
        'list': ListObject,
    }

    if isinstance(resp, dict):
        if 'data' in resp:
            if not isinstance(resp['data'], list):
                resp = resp.copy()
                resp = resp['data']

    if isinstance(resp, list):
        return [convert_to_svb_object(i, api_key, account) for i in resp]
    elif isinstance(resp, dict) and not isinstance(resp, SvbObject):
        resp = resp.copy()
        klass_name = resp.get('object')
        if isinstance(klass_name, string_types):
            klass = types.get(klass_name, SvbObject)
        else:
            klass = SvbObject
        return klass.construct_from(resp, api_key, svb_account=account)
    else:
        return resp


def convert_array_to_dict(arr):
    if isinstance(arr, list):
        d = {}
        for i, value in enumerate(arr):
            d[str(i)] = value
        return d
    else:
        return arr


def populate_headers(idempotency_key):
    if idempotency_key is not None:
        return {"Idempotency-Key": idempotency_key}
    return None


def _compute_diff(current, previous):
    if isinstance(current, dict):
        previous = previous or {}
        diff = current.copy()
        for key in set(previous.keys()) - set(diff.keys()):
            diff[key] = ""
        return diff
    return current if current is not None else ""


def _serialize_list(array, previous):
    array = array or []
    previous = previous or []
    params = {}

    for i, v in enumerate(array):
        previous_item = previous[i] if len(previous) > i else None
        if hasattr(v, 'serialize'):
            params[str(i)] = v.serialize(previous_item)
        else:
            params[str(i)] = _compute_diff(v, previous_item)

    return params


class SvbObject(dict):
    def __init__(self, id=None, api_key=None, svb_account=None,
                 hmac_key=None, **params):
        super(SvbObject, self).__init__()

        self._unsaved_values = set()
        self._transient_values = set()

        self._retrieve_params = params
        self._previous = None

        object.__setattr__(self, 'api_key', api_key)
        object.__setattr__(self, 'hmac_key', hmac_key)
        object.__setattr__(self, 'svb_account', svb_account)

        if id:
            self['id'] = id

    def update(self, update_dict):
        for k in update_dict:
            self._unsaved_values.add(k)
        return super(SvbObject, self).update(update_dict)

    def __setattr__(self, k, v):
        if k[0] == '_' or k in self.__dict__:
            return super(SvbObject, self).__setattr__(k, v)

        self[k] = v
        return None

    def __getattr__(self, k):
        if k[0] == '_':
            raise AttributeError(k)

        try:
            return self[k]
        except KeyError as err:
            raise AttributeError(*err.args)

    def __delattr__(self, k):
        if k[0] == '_' or k in self.__dict__:
            return super(SvbObject, self).__delattr__(k)
        else:
            del self[k]

    def __setitem__(self, k, v):
        if v == "":
            raise ValueError(
                "You cannot set %s to an empty string. "
                "We interpret empty strings as None in requests."
                "You may set %s.%s = None to delete the property" % (
                    k, str(self), k))

        super(SvbObject, self).__setitem__(k, v)

        # Allows for unpickling in Python 3.x
        if not hasattr(self, '_unsaved_values'):
            self._unsaved_values = set()

        self._unsaved_values.add(k)

    def __getitem__(self, k):
        try:
            return super(SvbObject, self).__getitem__(k)
        except KeyError as err:
            if k in self._transient_values:
                raise KeyError(
                    "%r.  HINT: The %r attribute was set in the past."
                    "It was then wiped when refreshing the object with "
                    "the result returned by Svb's API, probably as a "
                    "result of a save().  The attributes currently "
                    "available on this object are: %s" %
                    (k, k, ', '.join(self.keys())))
            else:
                raise err

    def __delitem__(self, k):
        super(SvbObject, self).__delitem__(k)

        # Allows for unpickling in Python 3.x
        if hasattr(self, '_unsaved_values'):
            self._unsaved_values.remove(k)

    @classmethod
    def construct_from(cls, values, key, svb_account=None):
        instance = cls(values.get('id'), api_key=key,
                       svb_account=svb_account)
        instance.refresh_from(values, api_key=key,
                              svb_account=svb_account)
        return instance

    def refresh_from(self, values, api_key=None, partial=False,
                     svb_account=None):
        self.api_key = api_key or getattr(values, 'api_key', None)
        self.svb_account = \
            svb_account or getattr(values, 'svb_account', None)

        # Wipe old state before setting new.  This is useful for e.g.
        # updating a customer, where there is no persistent card
        # parameter.  Mark those values which don't persist as transient
        if partial:
            self._unsaved_values = (self._unsaved_values - set(values))
        else:
            removed = set(self.keys()) - set(values)
            self._transient_values = self._transient_values | removed
            self._unsaved_values = set()
            self.clear()

        self._transient_values = self._transient_values - set(values)

        for k, v in iteritems(values):
            super(SvbObject, self).__setitem__(
                k, convert_to_svb_object(v, api_key, svb_account))

        self._previous = values

    @classmethod
    def api_base(cls):
        return None

    def request(self, method, url, params=None, headers=None):
        if params is None:
            params = self._retrieve_params
        requestor = api_requestor.APIRequestor(
            key=self.api_key, api_base=self.api_base(),
            account=self.svb_account, hmac_key=self.hmac_key)
        response, api_key = requestor.request(method, url, params, headers)

        return convert_to_svb_object(response, api_key, self.svb_account)

    def __repr__(self):
        ident_parts = [type(self).__name__]

        if isinstance(self.get('object'), string_types):
            ident_parts.append(self.get('object'))

        if isinstance(self.get('id'), string_types):
            ident_parts.append('id=%s' % (self.get('id'),))

        unicode_repr = '<%s at %s> JSON: %s' % (
            ' '.join(ident_parts), hex(id(self)), str(self))

        if sys.version_info[0] < 3:
            return unicode_repr.encode('utf-8')
        else:
            return unicode_repr

    def __str__(self):
        return util.json.dumps(self, sort_keys=True, indent=2)

    @property
    def svb_id(self):
        return self.id

    def serialize(self, previous):
        params = {}
        unsaved_keys = self._unsaved_values or set()
        previous = previous or self._previous or {}

        for k, v in self.items():
            if k == 'id' or (isinstance(k, str) and k.startswith('_')):
                continue
            elif isinstance(v, APIResource):
                continue
            elif hasattr(v, 'serialize'):
                params[k] = v.serialize(previous.get(k, None))
            elif k in unsaved_keys:
                params[k] = _compute_diff(v, previous.get(k, None))
            elif k == 'additional_owners' and v is not None:
                params[k] = _serialize_list(v, previous.get(k, None))

        return params

    # This class overrides __setitem__ to throw exceptions on inputs that it
    # doesn't like. This can cause problems when we try to copy an object
    # wholesale because some data that's returned from the API may not be valid
    # if it was set to be set manually. Here we override the class' copy
    # arguments so that we can bypass these possible exceptions on __setitem__.
    def __copy__(self):
        copied = SvbObject(self.get('id'), self.api_key,
                              svb_account=self.svb_account)

        copied._retrieve_params = self._retrieve_params

        for k, v in self.items():
            # Call parent's __setitem__ to avoid checks that we've added in the
            # overridden version that can throw exceptions.
            super(SvbObject, copied).__setitem__(k, v)

        return copied

    # This class overrides __setitem__ to throw exceptions on inputs that it
    # doesn't like. This can cause problems when we try to copy an object
    # wholesale because some data that's returned from the API may not be valid
    # if it was set to be set manually. Here we override the class' copy
    # arguments so that we can bypass these possible exceptions on __setitem__.
    def __deepcopy__(self, memo):
        copied = self.__copy__()
        memo[id(self)] = copied

        for k, v in self.items():
            # Call parent's __setitem__ to avoid checks that we've added in the
            # overridden version that can throw exceptions.
            super(SvbObject, copied).__setitem__(k, deepcopy(v, memo))

        return copied


class APIResource(SvbObject):

    @classmethod
    def retrieve(cls, id, api_key=None, **params):
        instance = cls(id, api_key, **params)
        instance.refresh()
        return instance

    def refresh(self):
        self.refresh_from(self.request('get', self.instance_url()))
        return self

    @classmethod
    def class_name(cls):
        if cls == APIResource:
            raise NotImplementedError(
                'APIResource is an abstract class.  You should perform '
                'actions on its subclasses (e.g. Charge, Customer)')
        return str(util.quote_plus(cls.__name__.lower()))

    @classmethod
    def class_url(cls):
        cls_name = cls.class_name()
        return "/v1/%ss" % (cls_name,)

    def instance_url(self):
        id = str(self.get('id'))
        if not id:
            raise error.InvalidRequestError(
                'Could not determine which URL to request: %s instance '
                'has invalid ID: %r' % (type(self).__name__, id), 'id')
        id = util.utf8(id)
        base = self.class_url()
        extn = util.quote_plus(id)
        return "%s/%s" % (base, extn)


class ListObject(SvbObject):

    def list(self, **params):
        return self.request('get', self['url'], params)

    def auto_paging_iter(self):
        page = self
        params = dict(self._retrieve_params)

        while True:
            item_id = None
            for item in page:
                item_id = item.get('id', None)
                yield item

            if not getattr(page, 'has_more', False) or item_id is None:
                return

            params['starting_after'] = item_id
            page = self.list(**params)

    def create(self, idempotency_key=None, **params):
        headers = populate_headers(idempotency_key)
        return self.request('post', self['url'], params, headers)

    def retrieve(self, id, **params):
        base = self.get('url')
        id = util.utf8(id)
        extn = util.quote_plus(id)
        url = "%s/%s" % (base, extn)

        return self.request('get', url, params)

    def __iter__(self):
        return getattr(self, 'data', []).__iter__()


class SingletonAPIResource(APIResource):

    @classmethod
    def retrieve(cls, **params):
        return super(SingletonAPIResource, cls).retrieve(None, **params)

    @classmethod
    def class_url(cls):
        cls_name = cls.class_name()
        return "/v1/%s" % (cls_name,)

    def instance_url(self):
        return self.class_url()


# Classes of API operations


class ListableAPIResource(APIResource):

    @classmethod
    def auto_paging_iter(cls, *args, **params):
        return cls.list(*args, **params).auto_paging_iter()

    @classmethod
    def list(cls, api_key=None, svb_account=None, hmac_key=None, **params):
        requestor = api_requestor.APIRequestor(api_key,
                                               api_base=cls.api_base(),
                                               account=svb_account,
                                               hmac_key=hmac_key)
        url = cls.class_url()
        response, api_key = requestor.request('get', url, params)
        svb_object = convert_to_svb_object(response, api_key,
                                                 svb_account)
        svb_object._retrieve_params = params
        return svb_object


class CreateableAPIResource(APIResource):

    @classmethod
    def create(cls, api_key=None, idempotency_key=None,
               svb_account=None, hmac_key=None, **params):
        requestor = api_requestor.APIRequestor(api_key,
                                               account=svb_account,
                                               hmac_key=hmac_key)
        url = cls.class_url()
        headers = populate_headers(idempotency_key)
        response, api_key = requestor.request('post', url, params, headers)
        return convert_to_svb_object(response, api_key, svb_account)


class UpdateableAPIResource(APIResource):

    @classmethod
    def _modify(cls, url, api_key=None, idempotency_key=None,
                svb_account=None, hmac_key=None, **params):
        requestor = api_requestor.APIRequestor(api_key,
                                               account=svb_account,
                                               hmac_key=hmac_key)
        headers = populate_headers(idempotency_key)
        response, api_key = requestor.request('post', url, params, headers)
        return convert_to_svb_object(response, api_key, svb_account)

    @classmethod
    def modify(cls, sid, **params):
        url = "%s/%s" % (cls.class_url(), util.quote_plus(util.utf8(sid)))
        return cls._modify(url, **params)

    def save(self, idempotency_key=None):
        updated_params = self.serialize(None)
        headers = populate_headers(idempotency_key)

        if updated_params:
            self.refresh_from(self.request('patch', self.instance_url(),
                                           updated_params, headers))
        else:
            util.logger.debug("Trying to save already saved object %r", self)
        return self


class DeletableAPIResource(APIResource):

    def delete(self, **params):
        self.refresh_from(self.request('delete', self.instance_url(), params))
        return self


# API objects
class Account(ListableAPIResource):
    @classmethod
    def retrieve(cls, id=None, api_key=None, **params):
        instance = cls(id, api_key, **params)
        instance.refresh()
        return instance

    @classmethod
    def modify(cls, id=None, **params):
        return cls._modify(cls._build_instance_url(id), **params)

    def instance_url(self):
        return self._build_instance_url(self.get('id'))


class ACH(CreateableAPIResource, ListableAPIResource,
          UpdateableAPIResource):
    @classmethod
    def class_url(cls):
        cls_name = cls.class_name()
        return "/v1/%s" % (cls_name,)


class Book(CreateableAPIResource, ListableAPIResource,
           UpdateableAPIResource):
    @classmethod
    def class_url(cls):
        cls_name = cls.class_name()
        return "/v1/%s" % (cls_name,)


class VirtualCard(CreateableAPIResource, ListableAPIResource,
                  UpdateableAPIResource, DeletableAPIResource):
    def email(self, email=None, idempotency_key=None):
        url = self.instance_url() + '/email'
        headers = populate_headers(idempotency_key)
        if email:
            params = {"email": email}
        else:
            params = {}
        self.refresh_from(
            self.request('post', url, params, headers)
        )
        return self


class Wire(CreateableAPIResource, ListableAPIResource,
           UpdateableAPIResource):
    @classmethod
    def class_url(cls):
        return "/v1/wire"


# Onboarding objects

class Company(CreateableAPIResource, ListableAPIResource,
              UpdateableAPIResource, DeletableAPIResource):
    @classmethod
    def class_url(cls):
        return "/v1/companies"


class Person(CreateableAPIResource, ListableAPIResource,
             UpdateableAPIResource, DeletableAPIResource):
    pass


class Login(CreateableAPIResource, ListableAPIResource,
            UpdateableAPIResource, DeletableAPIResource):
    pass


class ParentCompany(CreateableAPIResource, ListableAPIResource,
                    UpdateableAPIResource, DeletableAPIResource):
    @classmethod
    def class_url(cls):
        return "/v1/parent_companies"


class Address(CreateableAPIResource, ListableAPIResource,
              UpdateableAPIResource, DeletableAPIResource):
    @classmethod
    def class_url(cls):
        return "/v1/addresses"


class Document(CreateableAPIResource, ListableAPIResource,
               UpdateableAPIResource, DeletableAPIResource):
    pass


class GovernmentID(CreateableAPIResource, ListableAPIResource,
                   UpdateableAPIResource, DeletableAPIResource):
    @classmethod
    def class_url(cls):
        return "/v1/gov_idents"


class VerifyMixin(object):

    def verify(self, idempotency_key=None, **params):
        url = self.instance_url() + '/verify'
        headers = populate_headers(idempotency_key)
        self.refresh_from(self.request('post', url, params, headers))
        return self


class FileUpload(CreateableAPIResource, ListableAPIResource,
                 UpdateableAPIResource, DeletableAPIResource):
    @classmethod
    def api_base(cls):
        return upload_api_base

    @classmethod
    def class_name(cls):
        return 'file'

    @classmethod
    def create(cls, api_key=None, svb_account=None, **params):
        requestor = api_requestor.APIRequestor(
            api_key, api_base=cls.api_base(), account=svb_account)
        url = cls.class_url()
        supplied_headers = {
            "Content-Type": "multipart/form-data"
        }
        response, api_key = requestor.request(
            'post', url, params=params, headers=supplied_headers)
        return convert_to_svb_object(response, api_key, svb_account)
