from mmap import mmap
from numpy import ndarray
import pyecore
from pyecore.resources import ResourceSet, URI
import matplotlib.pyplot as plt
import networkx as nx
import os
import random
import numpy
import itertools


class ENCODE_M2G:
    id_iter = itertools.count()  # It Generates a new ID incrementally by each call
    map_iter = itertools.count(1)  # It Generates a new number incrementally by each call (it starts from 1)

    classes = []  # all classes inside metamodel
    unregulated_inheritance = []  # all classes inside metamodel with unsolved parent
    objects = []  # An array including all objects/elements in xmi file
    matrix_of_graph: ndarray = []  # 2D-Matrix of corresponding graph
    references_dictionary = {}  # A set of class references features by class name
    references_type_mapping = {}  # A dictionary that contains references mapped to numbers
    node_type = []  # 2D-Matrix containing node types(labels)
    true_containment_classes = []
    including_root = False  # Show that we consider root element as a node or not

    def __init__(self, metamodel_name, model_name):
        self.load_model(metamodel_name, model_name)

    def load_model(self, metamodel_name, model_name):
        """
        :param model_name:
        :param metamodel_name:
        :return:
        """
        rset = ResourceSet()
        resource = rset.get_resource(URI('../input/' + metamodel_name))
        mm_root = resource.contents[0]
        rset.metamodel_registry[mm_root.nsURI] = mm_root

        self.including_root = True
        self.extract_classes_references(mm_root)
        try:
            resource = rset.get_resource(URI('../input/' + model_name))
            model_root = resource.contents[0]
            if self.including_root:
                model_root._internal_id = next(self.id_iter)
                look_inside(model_root)
                self.node_type.append([model_root._internal_id, "root"])
            self.extract_objects_form_model(model_root)
            for h in self.node_type:
                print("node_id:", h[0], "node_type", h[1])
            for o in self.references_type_mapping:
                print("mapping->", o, " : ", self.references_type_mapping[o])
            # for i in self.references_dictionary:
            #     print("references_dictionary->", i, " : ", self.references_dictionary[i])
            for j in self.true_containment_classes:
                print("true_containment: ", j)
        except pyecore.valuecontainer.BadValueError:
            raise Exception("Sorry, Pyecore cannot pars the xmi file. please check the order of inside element.")
        return

    def extract_classes_references(self, metamodel_root):

        for e_class in metamodel_root.eClassifiers:
            if e_class.eClass.name is "EClass":
                self.classes.append(e_class.eStructuralFeatures.owner.name)
                references, containment_classes = self.extract_single_class_references(e_class)
                self.references_dictionary.update(references)
                append_items2list(containment_classes, self.true_containment_classes)
            else:
                # If there is a necessity for work on "EDataType", we can do it here!
                pass

        #  Completing the reference dictionary by adding parent references that are not available at first
        for e_class in self.unregulated_inheritance:
            references, containment_classes = self.extract_single_class_references(e_class)
            self.references_dictionary.update(references)

    def extract_single_class_references(self, e_class):
        """"
        :param e_class: The root class
        :return e_references:
        """
        true_containment_classes = []
        inner_references = []

        for ref in e_class.eStructuralFeatures:
            if ref.eClass.name == "EReference":  # Extracting inner relations
                inner_references.append(ref.name)
                if ref.name not in self.references_type_mapping:
                    self.references_type_mapping.update({ref.name: next(self.map_iter)})
                if ref.containment:
                    true_containment_classes.append(ref.name)

        # Creating references dictionary for the class
        references_dictionary = {e_class.name: inner_references}
        self.add_inheritance_references(e_class, references_dictionary)

        return references_dictionary, true_containment_classes

    def add_inheritance_references(self, e_class, references_dictionary):
        if len(e_class.eSuperTypes.items) > 0:  # It means the e_class has a parent
            if hasattr(e_class.eSuperTypes.items[0], "items"):  # It means the parent has another parent
                self.add_inheritance_references(e_class.eSuperTypes.items[0], references_dictionary)
            else:
                if e_class.eSuperTypes.items[0].name in self.references_dictionary:
                    # if parent is already in dictionary
                    references_dictionary.update(
                        {e_class.name: self.references_dictionary[e_class.eSuperTypes.items[0].name]})
                else:
                    # if parent doesn't exist in dictionary, add parent to dictionary
                    self.unregulated_inheritance.append(e_class)

    def extract_objects_form_model(self, root_object):
        """
        :param root_object: The root class
        :return:
        """
        for class_name in self.true_containment_classes:
            for obj in getattr(root_object, class_name):
                obj._internal_id = next(self.id_iter)  # Getting an ID for assign to each element
                self.node_type.append([obj._internal_id, obj._containment_feature.eType.name])
                # print("node name: ", obj.name, " -> node id: ", obj._internal_id)
                self.objects.append(obj)
                for inner_class_name in self.true_containment_classes:
                    if hasattr(obj, inner_class_name):
                        self.extract_objects_form_model(obj)

        # Create an empty 2D[len(input),len(input)] array as a matrix
        add_root_to_matrix = 0
        if self.including_root:
            add_root_to_matrix = 1
        self.matrix_of_graph = numpy.zeros(
            (len(self.objects) + add_root_to_matrix, len(self.objects) + add_root_to_matrix))
        for obj in self.objects:
            self.seek_in_depth(obj, self.references_dictionary)
        print("matrix shape is:", self.matrix_of_graph.shape, "\n", self.matrix_of_graph)

        return

    def create_graph(self, objects):
        node = NODE

    def seek_in_depth(self, obj, references_dictionary):
        """
        Checking inside relations and adding corresponding edges

        :param obj: The object that we want to extract all elements inside it
        :param references_dictionary: set of class references features by class name
        :return:
        """
        inner_references_name = references_dictionary[obj.eClass.name]

        for inner_ref_name in inner_references_name:
            if hasattr(obj, inner_ref_name):
                inner_element = getattr(obj, inner_ref_name)
                if inner_element is not None:  # check if references feature is not empty, try to find relation (edges)
                    if hasattr(inner_element, '_internal_id'):  # If we have a single inside element
                        if inner_element._internal_id is not None:
                            self.matrix_of_graph[obj._internal_id][inner_element._internal_id] = self.references_type_mapping[inner_ref_name]
                            if inner_element._internal_id is not 0:  # if inner_element is not root
                                self.check_and_add_relations_with_root(inner_element)
                            else:  # if obj is root add 1 for corresponding entry in matrix
                                self.matrix_of_graph[obj._container._internal_id][obj._internal_id] = self.references_type_mapping[inner_ref_name]
                    else:  # If we have a set of inside elements
                        set_elements = inner_element.items
                        for i in set_elements:
                            if i._internal_id is not None:
                                self.matrix_of_graph[obj._internal_id][i._internal_id] = self.references_type_mapping[inner_ref_name]
                                self.check_and_add_relations_with_root(i)

    def check_and_add_relations_with_root(self, obj):
        if self.including_root and obj._container._internal_id == 0:
            # Add an 1 for the root's relations
            self.matrix_of_graph[obj._internal_id][obj._container._internal_id] = self.references_type_mapping[obj._containment_feature.name]
            self.matrix_of_graph[obj._container._internal_id][obj._internal_id] = self.references_type_mapping[obj._containment_feature.name]


def look_inside(obj):
    """
    :param obj: The object that we want to look inside it
    """
    print(".............. Checking inside object .................")
    temp = vars(obj)
    for item in temp:
        print(item, ':', temp[item])
    print(".......................................................")


def append_items2list(input_list, cumulative_list):
    for item in input_list:
        cumulative_list.append(item)
    return cumulative_list


class NODE:
    id = 0
    type = ""
    information = []
    label = ""


class GRAPH:
    nodes = []


# if __name__ == "__main__":
#     ENCODE_M2G(metamodel_name="fsa.ecore", model_name="FSAModel.xmi")
# if __name__ == "__main__":
#     ENCODE_M2G(metamodel_name="basicfamily.ecore", model_name="FamilyRoot.xmi")
if __name__ == "__main__":
    ENCODE_M2G(metamodel_name="Tree.ecore", model_name="tree.xmi")




#     for ref in e_class.eStructuralFeatures.items:
#         if ref.eClass.name == "EReference":
#             e_references_temp.append(ref.name)
#             if ref.containment:
#                 true_containment_classes.append(ref.containment)
#             if ref.eOpposite is not None:
#                 e_opposites.append([ref.name, ref.eOpposite.name])
# def check_name_uniqueness(name_list):
#     """
#     Finding elements with the same name in input array and changing name of the last one
#
#     :param name_list: a String array
#     :return name_list: changed String array
#     """
#     k = 0
#     for item in name_list:
#         k += 1
#         for i in range(k, len(name_list), 1):
#             if item == name_list[i]:
#                 print("conflict founded: We have two references with name <", item, ">")
#                 n = random.randint(0, 10000)
#                 name_list[i] = item + str(n)
#     return name_list