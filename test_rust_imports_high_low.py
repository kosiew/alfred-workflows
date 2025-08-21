#!/usr/bin/env python3
import sys
sys.path.append('/Users/kosiew/GitHub/alfred-workflows/')
from process_text import (
    streamline_rust_imports_high,
    streamline_rust_imports_low,
)


def test_arrow_example_high():
    input_text = '''use arrow::array::{
    ArrayRef,
    RecordBatch,
    RecordBatchOptions,
    new_null_array,
};
use arrow::compute::can_cast_types;
use arrow::datatypes::{
    DataType,
    Field,
    Schema,
    SchemaRef,
};'''

    expected = '''use arrow::{
    array::{new_null_array, ArrayRef, RecordBatch, RecordBatchOptions},
    compute::can_cast_types,
    datatypes::{DataType, Field, Schema, SchemaRef},
};'''

    assert streamline_rust_imports_high(input_text).strip() == expected.strip()


def test_arrow_example_low():
    input_text = '''use arrow::array::{
    ArrayRef,
    RecordBatch,
    RecordBatchOptions,
    new_null_array,
};
use arrow::compute::can_cast_types;
use arrow::datatypes::{
    DataType,
    Field,
    Schema,
    SchemaRef,
};'''

    expected = '''use arrow::array::{
    ArrayRef,
    RecordBatch,
    RecordBatchOptions,
    new_null_array,
};
use arrow::compute::can_cast_types;
use arrow::datatypes::{
    DataType,
    Field,
    Schema,
    SchemaRef,
};'''

    assert streamline_rust_imports_low(input_text).strip() == expected.strip()


def test_std_example_high_low():
    input_text = '''use std::io::{self, Read};
use std::io::BufReader;
use std::fmt::Display;'''

    expected_high = '''use std::{
    io::{self, BufReader, Read},
    fmt::Display,
};'''

    expected_low = '''use std::fmt::Display;
use std::io::{
    BufReader,
    Read,
    self,
};'''

    assert streamline_rust_imports_high(input_text).strip() == expected_high.strip()
    assert streamline_rust_imports_low(input_text).strip() == expected_low.strip()
