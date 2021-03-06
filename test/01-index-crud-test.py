# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

import random

import mango


class IndexCrudTests(mango.DbPerClass):
    def test_bad_fields(self):
        bad_fields = [
            None,
            True,
            False,
            "bing",
            2.0,
            {"foo": "bar"},
            [{"foo": 2}],
            [{"foo": "asc", "bar": "desc"}],
            [{"foo": "asc"}, {"bar": "desc"}]
        ]
        for fields in bad_fields:
            try:
                self.db.create_index(fields)
            except Exception, e:
                assert e.response.status_code == 400
            else:
                raise AssertionError("bad create index")

    def test_bad_types(self):
        bad_types = [
            None,
            True,
            False,
            1.5,
            "foo", # Future support
            "geo", # Future support
            {"foo": "bar"},
            ["baz", 3.0]
        ]
        for bt in bad_types:
            try:
                self.db.create_index(["foo"], idx_type=bt)
            except Exception, e:
                assert e.response.status_code == 400, (bt, e.response.status_code)
            else:
                raise AssertionError("bad create index")

    def test_bad_names(self):
        bad_names = [
            True,
            False,
            1.5,
            {"foo": "bar"},
            [None, False]
        ]
        for bn in bad_names:
            try:
                self.db.create_index(["foo"], name=bn)
            except Exception, e:
                assert e.response.status_code == 400
            else:
                raise AssertionError("bad create index")
            try:
                self.db.create_index(["foo"], ddoc=bn)
            except Exception, e:
                assert e.response.status_code == 400
            else:
                raise AssertionError("bad create index")

    def test_create_idx_01(self):
        fields = ["foo", "bar"]
        ret = self.db.create_index(fields, name="idx_01")
        assert ret is True
        for idx in self.db.list_indexes():
            if idx["name"] != "idx_01":
                continue
            assert idx["def"]["fields"] == [{"foo": "asc"}, {"bar": "asc"}]
            return
        raise AssertionError("index not created")

    def test_create_idx_01_exists(self):
        fields = ["foo", "bar"]
        ret = self.db.create_index(fields, name="idx_01")
        assert ret is False

    def test_create_idx_02(self):
        fields = ["baz", "foo"]
        ret = self.db.create_index(fields, name="idx_02")
        assert ret is True
        for idx in self.db.list_indexes():
            if idx["name"] != "idx_02":
                continue
            assert idx["def"]["fields"] == [{"baz": "asc"}, {"foo": "asc"}]
            return
        raise AssertionError("index not created")

    def test_read_idx_doc(self):
        for idx in self.db.list_indexes():
            if idx["type"] == "special":
                continue
            ddocid = idx["ddoc"]
            doc = self.db.open_doc(ddocid)
            assert doc["_id"] == ddocid
            info = self.db.ddoc_info(ddocid)
            assert info["name"] == ddocid

    def test_delete_idx_escaped(self):
        pre_indexes = self.db.list_indexes()
        ret = self.db.create_index(["bing"], name="idx_del_1")
        assert ret is True
        for idx in self.db.list_indexes():
            if idx["name"] != "idx_del_1":
                continue
            assert idx["def"]["fields"] == [{"bing": "asc"}]
            self.db.delete_index(idx["ddoc"].replace("/", "%2F"), idx["name"])
        post_indexes = self.db.list_indexes()
        assert pre_indexes == post_indexes

    def test_delete_idx_unescaped(self):
        pre_indexes = self.db.list_indexes()
        ret = self.db.create_index(["bing"], name="idx_del_2")
        assert ret is True
        for idx in self.db.list_indexes():
            if idx["name"] != "idx_del_2":
                continue
            assert idx["def"]["fields"] == [{"bing": "asc"}]
            self.db.delete_index(idx["ddoc"], idx["name"])
        post_indexes = self.db.list_indexes()
        assert pre_indexes == post_indexes

    def test_delete_idx_no_design(self):
        pre_indexes = self.db.list_indexes()
        ret = self.db.create_index(["bing"], name="idx_del_3")
        assert ret is True
        for idx in self.db.list_indexes():
            if idx["name"] != "idx_del_3":
                continue
            assert idx["def"]["fields"] == [{"bing": "asc"}]
            self.db.delete_index(idx["ddoc"].split("/")[-1], idx["name"])
        post_indexes = self.db.list_indexes()
        assert pre_indexes == post_indexes

    def test_bulk_delete(self):
        fields = ["field1"]
        ret = self.db.create_index(fields, name="idx_01")
        assert ret is True

        fields = ["field2"]
        ret = self.db.create_index(fields, name="idx_02")
        assert ret is True

        fields = ["field3"]
        ret = self.db.create_index(fields, name="idx_03")
        assert ret is True

        docids = []

        for idx in self.db.list_indexes():
            if idx["ddoc"] is not None:
                docids.append(idx["ddoc"])

        docids.append("_design/this_is_not_an_index_name")

        ret = self.db.bulk_delete(docids)

        assert ret["fail"][0]["id"] == "_design/this_is_not_an_index_name"
        assert len(ret["success"]) == 3

        for idx in self.db.list_indexes():
            assert idx["type"] != "json"
            assert idx["type"] != "text"

    def test_recreate_index(self):
        pre_indexes = self.db.list_indexes()
        for i in range(5):
            ret = self.db.create_index(["bing"], name="idx_recreate")
            assert ret is True
            for idx in self.db.list_indexes():
                if idx["name"] != "idx_recreate":
                    continue
                assert idx["def"]["fields"] == [{"bing": "asc"}]
                self.db.delete_index(idx["ddoc"], idx["name"])
                break
            post_indexes = self.db.list_indexes()
            assert pre_indexes == post_indexes

    def test_delete_misisng(self):
        # Missing design doc
        try:
            self.db.delete_index("this_is_not_a_design_doc_id", "foo")
        except Exception, e:
            assert e.response.status_code == 404
        else:
            raise AssertionError("bad index delete")

        # Missing view name
        indexes = self.db.list_indexes()
        not_special = [idx for idx in indexes if idx["type"] != "special"]
        idx = random.choice(not_special)
        ddocid = idx["ddoc"].split("/")[-1]
        try:
            self.db.delete_index(ddocid, "this_is_not_an_index_name")
        except Exception, e:
            assert e.response.status_code == 404
        else:
            raise AssertionError("bad index delete")

        # Bad view type
        try:
            self.db.delete_index(ddocid, idx["name"], idx_type="not_a_real_type")
        except Exception, e:
            assert e.response.status_code == 404
        else:
            raise AssertionError("bad index delete")

    def test_limit_skip_index(self):
        fields = ["field1"]
        ret = self.db.create_index(fields, name="idx_01")
        assert ret is True

        fields = ["field2"]
        ret = self.db.create_index(fields, name="idx_02")
        assert ret is True

        fields = ["field3"]
        ret = self.db.create_index(fields, name="idx_03")
        assert ret is True

        assert len(self.db.list_indexes(limit=2)) == 2
        assert len(self.db.list_indexes(limit=5,skip=4)) == 2
        assert len(self.db.list_indexes(skip=5)) == 1
        assert len(self.db.list_indexes(skip=6)) == 0
        assert len(self.db.list_indexes(skip=100)) == 0
        assert len(self.db.list_indexes(limit=10000000)) == 6

        try:
            self.db.list_indexes(skip=-1)
        except Exception, e:
            assert e.response.status_code == 500

        try:
            self.db.list_indexes(limit=0)
        except Exception, e:
            assert e.response.status_code == 500
