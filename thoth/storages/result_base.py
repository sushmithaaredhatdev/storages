#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# thoth-storages
# Copyright(C) 2018 Fridolin Pokorny
#
# This program is free software: you can redistribute it and / or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""Adapter for storing analysis results onto a persistence remote store."""

import os
import typing

from .base import StorageBase
from .ceph import CephStore
from .result_schema import RESULT_SCHEMA
from .exceptions import SchemaError


class ResultStorageBase(StorageBase):
    """Adapter base for storing results."""

    RESULT_TYPE = None

    def __init__(self, deployment_name=None, *,
                 host: str=None, key_id: str=None, secret_key: str=None, bucket: str=None, region: str=None,
                 prefix: str=None):
        """Initialize result storage database.

        The adapter can take arguments from env variables if not provided explicitly.
        """
        assert self.RESULT_TYPE is not None, "Make sure you define RESULT_TYPE in derived classes " \
                                             "to distinguish between adapter type instances."

        self.deployment_name = deployment_name or os.environ['THOTH_DEPLOYMENT_NAME']
        self.prefix = "{}/{}/{}".format(
            prefix or os.environ['THOTH_CEPH_BUCKET_PREFIX'],
            self.deployment_name,
            self.RESULT_TYPE
        )
        self.ceph = CephStore(
            self.prefix,
            host=host,
            key_id=key_id,
            secret_key=secret_key,
            bucket=bucket,
            region=region
        )

    @classmethod
    def get_document_id(cls, document: dict) -> str:
        """Get document id under which the given document should be stored."""
        # We use hostname that matches pod id generated by OpenShift so document id
        # matches returned pod id on user API endpoint.
        return document['metadata']['hostname']

    def is_connected(self) -> bool:
        """Check if the given database adapter is in connected state."""
        return self.ceph.is_connected()

    def connect(self) -> None:
        """Connect the given storage adapter."""
        self.ceph.connect()

    def get_document_listing(self) -> typing.Generator[str, None, None]:
        """Get listing of documents available in Ceph as a generator."""
        return self.ceph.get_document_listing()

    def store_document(self, document: dict) -> str:
        """Store the given document in Ceph."""
        try:
            RESULT_SCHEMA(document)
        except Exception as exc:
            raise SchemaError("Failed to validate document schema") from exc

        document_id = self.get_document_id(document)
        self.ceph.store_document(document, document_id)
        return document_id

    def retrieve_document(self, document_id: str) -> dict:
        """Retrieve a document from Ceph by its id."""
        return self.ceph.retrieve_document(document_id)

    def iterate_results(self) -> typing.Generator[tuple, None, None]:
        """Iterate over results available in the Ceph."""
        return self.ceph.iterate_results()
