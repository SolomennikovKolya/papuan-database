"""Санитарные тесты декларативных описаний сущностей."""

from __future__ import annotations

from app.models.base import Base
from app.ui.crud.descriptor import FieldKind
from app.ui.descriptors import (
    REFERENCE_DESCRIPTORS,
    TRAINING_DESCRIPTORS,
    TRIP_DESCRIPTORS,
)

ALL_DESCRIPTORS = (
    *REFERENCE_DESCRIPTORS,
    *TRAINING_DESCRIPTORS,
    *TRIP_DESCRIPTORS,
)


class TestDescriptors:
    def test_every_descriptor_describes_a_model(self) -> None:
        for d in ALL_DESCRIPTORS:
            assert issubclass(d.model, Base), f"{d.title}: model должен наследовать Base"

    def test_columns_reference_real_attributes(self) -> None:
        for d in ALL_DESCRIPTORS:
            for col in d.columns:
                root = col.field.split(".", 1)[0]
                assert hasattr(d.model, root), (
                    f"{d.title}: колонка {col.field!r} ссылается на отсутствующий атрибут {root!r}"
                )

    def test_form_field_relations_have_model(self) -> None:
        for d in ALL_DESCRIPTORS:
            for f in d.form_fields:
                if f.kind == FieldKind.RELATION:
                    assert f.relation_model is not None, (
                        f"{d.title}: relation-поле {f.name!r} без relation_model"
                    )

    def test_perm_prefix_non_empty(self) -> None:
        for d in ALL_DESCRIPTORS:
            assert d.perm_prefix, f"{d.title}: пустой perm_prefix"
