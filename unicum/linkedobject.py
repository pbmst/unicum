# -*- coding: utf-8 -*-

#  unicum
#  ------------
#  Simple object cache and __factory.
#
#  Author:  pbrisk <pbrisk_at_github@icloud.com>
#  Copyright: 2016, 2017 Deutsche Postbank AG
#  Website: https://github.com/pbrisk/unicum
#  License: APACHE Version 2 License (see LICENSE file)


import inspect
import weakref

class WeakAttrLink(object):

    __slots__ = ['_attr', '_ref_name', '_ref']

    def __init__(self, obj, attr):
        #self._ref_name =  str(obj)
        self._ref = weakref.ref(obj)
        self._attr = attr

    @property
    def ref_obj(self):
        return self._ref()

    @property
    def attr(self):
        return self._attr

    def __call__(self):
        obj = self.ref_obj
        try:
            attr = getattr(obj, self.attr)
        except AttributeError:
            attr = None

        return attr

    def __eq__(self, other):
        return self.ref_obj == other.ref_obj and self.attr == other.attr

    def __repr__(self):
        return "WeakAttrLink({})".format(repr(self.ref_obj) + ', ' + self.attr)

    def __hash__(self):
        return hash((self._ref, self.attr))


class LinkedObject(object):
    """ links from linked_obj to (obj, attribute) with obj.attribute = linked_obj """
    __link = dict()

    @property
    def _name(self):
        return str(self)

    @classmethod
    def _get_links(cls):
        mro = inspect.getmro(cls)
        for m in mro:
            attr = '_' + m.__name__ + '__link'
            if hasattr(cls, attr):
                return getattr(cls, attr)
        raise TypeError

    def __repr__(self):
        return self.__class__.__name__ + '.' + str(self) + '(' + str(id(self)) + ')'

    def __str__(self):
        return str(self.__class__.__name__)

    def __setattr__(self, item, value):
        if hasattr(self, item):
            current = getattr(self, item)
            if isinstance(current, LinkedObject):
                current.remove_link(self, item)
        super(LinkedObject, self).__setattr__(item, value)
        if isinstance(value, LinkedObject) and value._name:
            value.register_link(self, item)


    def register_link(self, obj, attr=None):
        """
        creates link from obj.attr to self
        :param obj: object to register link to
        :param attr: attribute name to register link to
        """
        name = self._name
        if not name:
            return self
        l = self.__class__._get_links()
        if name not in l:
            l[name] = set()
        v = WeakAttrLink(obj, attr)
        if v not in l[name]:
            l[name].add(v)
        return self

    def remove_link(self, obj, attr=None):
        """
        removes link from obj.attr
        """
        name = self._name
        if not name:
            return self
        l = self.__class__._get_links()
        v = WeakAttrLink(None, obj) if attr is None else WeakAttrLink(obj, attr)
        if name in l:
            if v in l[name]:
                l[name].remove(v)
            if not l[name]:
                l.pop(name)
        return self

    def update_link(self):
        """
        redirects all links to self (the new linked object)
        """
        name = self._name
        if not name:
            return self
        l = self.__class__._get_links()
        to_be_changed = list()
        if name in l:

            for wal in l[name]:
                if wal.ref_obj and self is not wal():
                    to_be_changed.append((wal.ref_obj, wal.attr))

        for o, a in to_be_changed:
            setattr(o, a, self)

        self.clean_up_link_dict()
        return self

    def clean_up_link_dict(self):
        links = self._get_links()
        names_to_remove = list()
        for name in links:
            wal_to_remove = set()
            for wal in links[name]:
                if not wal.ref_obj:
                    wal_to_remove.add(wal)
            links[name].difference_update(wal_to_remove)
            if not links[name]:
                names_to_remove.append(name)

        for name in names_to_remove:
            links.pop(name)