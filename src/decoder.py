import networkx as nx
from numpy import ndarray
import pyecore
from pyecore.resources import ResourceSet, URI
from pyecore.resources.xmi import XMIResource
from scipy.sparse import csr_matrix
import numpy
from pathlib import Path
import itertools
import random
from datetime import datetime


def create_xmi_file(root):
    time = datetime.now().strftime('%m%d%H%M%S')
    Path("../output").mkdir(parents=True, exist_ok=True)
    resource = XMIResource(URI('initial.xmi'))
    resource.append(root)  # We add the root to the resource
    resource.save()  # will save the result in 'initial.xmi'
    resource.save(output=URI('../output/' + root.eClass.name + time + '.xmi'))  # save the result in 'output.xmi'


class DECODE_G2M:
    name_iter = itertools.count(1)  # It Generates a new number incrementally by each call (it starts from 1)
    adj_matrix = []
    classes = {}  # all classes inside metamodel
    enum_dict = {}  # A set of class's EEnum by enum name
    obj_attrs_dict = {}  # A set of class's Attributes by class name
    references_type_mapping = {}  # A dictionary that contains references mapped to numbers
    references_pair_dictionary = {}  # A set of pair class and their reference
    mm_root = []

    def __init__(self, mm_root, classes, obj_attrs_dict, references_type_mapping, references_pair_dictionary, enum_dict,
                 obj_types, adj_matrix):
        self.mm_root = mm_root
        self.classes = classes
        self.obj_attrs_dict = obj_attrs_dict
        self.references_type_mapping = references_type_mapping
        self.references_pair_dictionary = references_pair_dictionary
        self.enum_dict = enum_dict
        self.create_initial_objects(self.get_obj_types(obj_types), adj_matrix)
        print("Here in decoder.....")
        # for i in obj_types:
        #     print("obj_type: ", i)

    def get_obj_types(self, node_types):
        obj_types = []
        for i in node_types:
            for key, value in self.classes.items():
                if i[1] == value:
                    obj_types.append(key)
        return obj_types

    def create_initial_objects(self, obj_types, adj_matrix):
        # Creating an initial instance of each class existed in metamodel
        init_objects = {}
        class_items = self.classes.items()
        for e_class in self.mm_root.eClassifiers:
            for node_type in class_items:
                # print("create_initial_objects -> e_class.name:", e_class.name)
                if hasattr(e_class, 'serializable'):
                    print("{"+e_class.name + "} is ENum!")
                elif e_class.abstract:
                    print("{"+e_class.name + "} is abstract!")
                elif e_class.name == node_type[0]:
                    # print("create_initial_objects -> node_type[0]:", node_type[0])
                    obj = e_class()
                    obj.name = e_class.name
                    init_objects.update({e_class.name: obj})
        self.create_model(init_objects, obj_types, adj_matrix)

    def create_model(self, init_objects, generated_model_type_list, adj_matrix):
        elements = []
        for obj_type in generated_model_type_list:
            new_obj = init_objects[obj_type].eClass()
            new_obj = self.set_obj_attrs(new_obj)
            elements.append(new_obj)
            # print("new_obj:", new_obj.eClass)

        typed_matrix = adj_matrix
        n = len(elements)
        for i in range(0, n):
            for j in range(0, n):
                if adj_matrix[i][j] > 0:
                    rel_dict = self.references_pair_dictionary[generated_model_type_list[i]]
                    if len(rel_dict) > 0:
                        for ref in rel_dict:
                            # print("ref [0]:", ref[0], "__ rel_dict:", rel_dict)
                            if ref[0] == generated_model_type_list[j]:
                                # print("element.eClass.name:", elements[i].eClass.name)
                                # print("ref[1]:", ref[1])
                                # print("___ has Attribute _", getattr(elements[i], ref[1]))
                                if getattr(elements[i], ref[1]) is not None:
                                    # print("subElement:", elements[j])
                                    getattr(elements[i], ref[1]).append(elements[j])
                                    typed_matrix[i][j] = self.references_type_mapping[ref[1]]
                                    typed_matrix[j][i] = typed_matrix[i][j]
        print("_________\n", typed_matrix)
        root = elements[0]
        create_xmi_file(root)
        return typed_matrix

    def set_obj_attrs(self, obj):
        object_attrs = self.obj_attrs_dict[obj.eClass.name]
        if len(object_attrs) > 0:
            for attr in object_attrs:
                if attr[1] == "EString":
                    setattr(obj, attr[0], attr[0] + str(next(self.name_iter)))
                elif attr[1] == "EInt" or attr[1] == "EShort" or attr[1] == "ELong":
                    setattr(obj, attr[0], random.randint(10, 80))
                elif attr[1] == "EDate":
                    setattr(obj, attr[0], datetime.now())
                elif attr[1] == "EFloat":
                    setattr(obj, attr[0], random.randint(10, 80) + random.choice([0.1, 0.25, 0.25, 0.75, 0.9]))
                elif attr[1] == "EBoolean":
                    setattr(obj, attr[0], random.choice([True, False]))
                for enum in self.enum_dict:
                    if attr[1] == enum:
                        setattr(obj, attr[0], random.choice(self.enum_dict[enum]))
        return obj
