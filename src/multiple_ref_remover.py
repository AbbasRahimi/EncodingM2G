import itertools
from datetime import datetime

from pyecore.resources import ResourceSet, URI
from pyecore.ecore import EClass, EReference, EObject, EString, EPackage, EAttribute


class multiple_ref_remover:
    id_iter = itertools.count()
    e_package = []
    refined_metamodel = []
    true_containment_classes = []

    def __init__(self, mm_name, instance_name):
        # Load the Ecore file
        ecore_file = f'../input/{mm_name}.ecore'
        resource_set = ResourceSet()
        resource = resource_set.get_resource(URI(ecore_file))
        self.e_package = resource.contents[0]  # Assuming there's only one root package in the file
        self.refine_mm()
        self.remove_pair_references(instance_name)

    def refine_mm(self):
        # Get all EClasses from the package
        eclasses = [element for element in self.e_package.eAllContents() if isinstance(element, EClass)]

        root = eclasses[0]

        for e_class in eclasses:
            # print("eclass:: ", e_class.name)
            for ref in e_class.eStructuralFeatures:
                if isinstance(ref, EReference) and ref.containment:
                    self.true_containment_classes.append(ref.name)
                    print("eclass:: ", ref.name)

        # Find pairs of EClasses with more than one reference to each other
        referencing_pairs = self.find_referencing_pairs(eclasses)

        # Create and replace references with a mediator EClass
        for ref_pair in referencing_pairs:
            self.create_mediator_eclass(ref_pair, root)

        # Remove old references
        self.remove_old_references(referencing_pairs)

        # save the refined metamodel
        self.save_new_mm()

    def create_mediator_eclass(self, ref_pairs, root):
        eclass1 = ref_pairs[0]
        eclass2 = ref_pairs[1]
        references = ref_pairs[2]

        for ref_pair in references:
            mediator_eclass = EClass(name=f"{eclass1.name[:2]}_{ref_pair.name}_Mediator_{eclass2.name[:2]}")

            # Add mediator EClass to the package
            self.e_package.eClassifiers.append(mediator_eclass)

            # Create references from eclass1 to mediator and mediator to eclass2
            upper_bound = ref_pair.upperBound if hasattr(ref_pair, 'upperBound') else -1
            lower_bound = ref_pair.lowerBound if hasattr(ref_pair, 'lowerBound') else 0
            r2m_name = f"{eclass1.name[:2]}_to_{ref_pair.name}_Mediator"
            m2r_name = f"{ref_pair.name}_Mediator_to_{eclass2.name[:2]}"
            ref_to_mediator = EReference(name=r2m_name, upper=upper_bound, lower=lower_bound, eType=mediator_eclass)
            ref_from_mediator = EReference(name=m2r_name, upper=upper_bound, lower=lower_bound, eType=eclass2)
            eclass1.eStructuralFeatures.append(ref_to_mediator)
            mediator_eclass.eStructuralFeatures.append(ref_from_mediator)

            # Create references to the root class
            ref1_to_root = EReference(name=f"{eclass1.name[:2]}_{ref_pair.name}_Mediator_to_root", upper=-1,
                                      eType=mediator_eclass,
                                      containment=True)
            root.eStructuralFeatures.append(ref1_to_root)

        return mediator_eclass

    def find_referencing_pairs(self, eclasses):
        referencing_pairs = []
        for eclass1 in eclasses:
            for eclass2 in eclasses:
                if eclass1 is not eclass2:  # TODO remove this statement to include self-loops
                    references_in_between = []
                    e_opp_refs_in_between = []
                    for ref1 in eclass1.eAllReferences():
                        if ref1.eType is eclass2:
                            references_in_between.append(ref1)
                            # manage EOpposites
                            if ref1.eOpposite is not None:
                                e_opp_refs_in_between.append(ref1.eOpposite)

                    if len(references_in_between) > 1:
                        e_opp_refs = eclass2, eclass1, e_opp_refs_in_between
                        if not self.check_seen_ref(e_opp_refs, referencing_pairs):
                            referencing_pairs.append((eclass1, eclass2, references_in_between))
                            print("eclass1:", eclass1, "eclass2:", eclass2, "\n-> : ", references_in_between)

        return referencing_pairs

    def remove_old_references(self, referencing_pairs):
        for eclass1, eclass2, ref_pairs in referencing_pairs:
            for ref in eclass1.eAllReferences():
                for reference in ref_pairs:
                    if ref.name is reference.name:
                        # print("Reference ", ref, " is removed from class ", eclass1)
                        eclass1.eStructuralFeatures.remove(ref)
                        if ref.eOpposite is not None:
                            eclass2.eStructuralFeatures.remove(ref.eOpposite)
                            # print("Reference ", ref.eOpposite, " is removed from class ", eclass2)
            for ref in eclass2.eAllReferences():
                for reference in ref_pairs:
                    if ref.name is reference.name:
                        # print("Reference ", ref, " is removed from class ", eclass2)
                        eclass2.eStructuralFeatures.remove(ref)
                        if ref.eOpposite is not None:
                            eclass1.eStructuralFeatures.remove(ref.eOpposite)
                            # print("Reference ", ref.eOpposite, " is removed from class ", eclass1)

    def save_new_mm(self):
        # Serialize the updated Ecore model to a new Ecore file
        output_file = '../output1/output_file' + datetime.now().strftime(
            '%H%M%S') + '.ecore'  # Change this to the desired output file path
        resource_set = ResourceSet()
        output_resource = resource_set.create_resource(URI(output_file))
        output_resource.append(self.e_package)
        output_resource.save()
        self.refined_metamodel = output_resource

    def check_seen_ref(self, e_opp_refs, referencing_pairs):
        temp = False
        for ref_pair in referencing_pairs:
            if ref_pair[0].name is e_opp_refs[0].name:
                if ref_pair[1].name is e_opp_refs[1].name:
                    e_opp_set = set(e_opp_refs[2])
                    ref_set = set(ref_pair[2])
                    temp = e_opp_set.issubset(ref_set)
        return temp

    def remove_pair_references(self, original_instance_model):
        # Step 1: Load the original instance model from the XMI file
        resource_set = ResourceSet()
        resource = resource_set.get_resource(URI('../input/' + original_instance_model))
        original_root_object = resource.contents[0]
        self.extract_objects_form_model(original_root_object)

        # Step 2: Create a new instance model conforming to the metamodel without pair references
        # new_root_object = self.create_new_instance_model(self.refined_metamodel)

        # Step 3: Traverse the original instance model and populate the new model without pair references
        # self.traverse_and_populate(original_root_object, new_root_object)

        # Save the new instance model to a new XMI file
        # new_model_file = "new_instance_model.xmi"
        # new_resource = resource_set.create_resource(URI(new_model_file))
        # new_resource.append(new_root_object)
        # new_resource.save()

    def extract_objects_form_model(self, root_object):
        """
        :param root_object: The root class
        """
        package_name = root_object.eClass.name
        new_package = EPackage(package_name)
        new_package.nsURI = 'http://' + package_name + '.com'
        new_package.nsPrefix = package_name
        # temp = self.refined_metamodel
        print("new package name nsURI:: ", new_package.nsURI, "_ root obj:: ", root_object)
        getattr(new_package, 'eClassifiers').append(EClass("House"))
        for k in new_package.eClassifiers:
            print("new_package.eClassifiers: ", k)
        objects = []
        for ref_name in self.true_containment_classes:
            # print("ref_name: ", ref_name)
            if hasattr(root_object, ref_name):
                all_instances_by_same_class_name = getattr(root_object, ref_name)
            if hasattr(all_instances_by_same_class_name, "items"):  # if we have several items in same type
                for obj in all_instances_by_same_class_name:
                    if obj not in objects:
                        # self.print_inner_elements(obj)
                        obj._internal_id = next(self.id_iter)  # Getting an ID for assigning to each element
                        self.create_new_instance_model(obj)
                        # self.node_types.append([obj._internal_id, self.classes[obj.eClass.name]])
                        # self.objects.append(obj)
                        for inner_class_name in self.true_containment_classes:
                            if hasattr(obj, inner_class_name):
                                self.extract_objects_form_model(obj)
            elif all_instances_by_same_class_name is not None:  # if we have just one item
                all_instances_by_same_class_name._internal_id = next(
                    self.id_iter)  # generating an ID for assign to the element
                # self.node_types.append([all_instances_by_same_class_name._internal_id,
                #                         self.classes[all_instances_by_same_class_name._containment_feature.eType.name]])
                # self.objects.append(all_instances_by_same_class_name)
                for inner_class_name in self.true_containment_classes:
                    if hasattr(all_instances_by_same_class_name, inner_class_name):
                        self.extract_objects_form_model(all_instances_by_same_class_name)

    def print_inner_elements(self, eobject):
        eclass = eobject.eClass
        for feature in eclass.eAllStructuralFeatures():
            if isinstance(feature, EAttribute):
                value = getattr(eobject, feature.name)
                if isinstance(value, EObject):
                    self.print_inner_elements(value)
                else:
                    print("feature:", f" {feature.name}: {value}")
            elif isinstance(feature, EReference):
                # print("++ref is founded ", feature)
                if hasattr(feature, 'name'):
                    print("ref_name: ", feature.name)

    def create_new_instance_model(self, eobject):
        eclass = eobject.eClass
        for feature in eclass.eAllStructuralFeatures():
            if isinstance(feature, EAttribute):
                value = getattr(eobject, feature.name)
                if isinstance(value, EObject):
                    self.create_new_instance_model(value)
                else:
                    print("feature:", f" {feature.name}: {value}")
            elif isinstance(feature, EReference):
                # print("++ref is founded ", feature)
                if hasattr(feature, 'name'):
                    print("ref_name: ", feature.name)


if __name__ == "__main__":
    multiple_ref_remover(mm_name="RetalSystem", instance_name="RentalSystem.xmi")













    # def create_new_instance_model1(self, package_name):
    #     # Step 2: Create and return a new instance model
    #     # In this example, let's assume a simple metamodel with two classes: Person and House
    #     # The Person class has a reference to House (address) and an additional reference (home_address).
    #     person_package = EPackage(package_name)
    #     person_package.nsURI = 'http://' + package_name + '.com'
    #     person_package.nsPrefix = package_name
    #
    #     Person = EClass('Person')
    #     House = EClass('House')
    #     person_package.eClassifiers.extend([Person, House])
    #
    #     # Add the attributes to the classes (e.g., name, street, city)
    #     name_attr = EString('name')
    #     street_attr = EString('street')
    #     city_attr = EString('city')
    #     Person.eStructuralFeatures.extend([name_attr, EReference('address', House)])
    #     House.eStructuralFeatures.extend([street_attr, city_attr])
    #
    #     # Add the additional reference (home_address) to the Person class
    #     home_address_ref = EReference('home_address', House)
    #     Person.eStructuralFeatures.append(home_address_ref)
    #
    #     # Create the root object for the new instance model
    #     new_root_object = Person()
    #
    #     return new_root_object

 #
 #
 #
 # def traverse_and_populate(self, original_object, new_object):
 #        # Step 3: Traverse the original instance model, populate the new instance model, and handle pair references
 #
 #        # In this example, let's assume the original model has instances of the Person class with addresses.
 #        # We will traverse the original model, create corresponding objects in the new model,
 #        # and set their attributes and references accordingly.
 #
 #        if isinstance(original_object, EObject) and isinstance(new_object, EObject):
 #            # Set the 'name' attribute for the Person
 #            if 'name' in original_object.eClass.eAllAttributes:
 #                new_object.name = original_object.name
 #
 #            # Create a new Address object and set its attributes
 #            if 'address' in original_object.eClass.eAllReferences:
 #                original_address = original_object.address
 #                new_house = EClass('House')
 #                new_house.street = original_address.street
 #                new_house.city = original_address.city
 #                new_object.address = new_house
 #
 #            # Handle the additional reference (home_address)
 #            if 'home_address' in original_object.eClass.eAllReferences:
 #                original_home_address = original_object.home_address
 #                new_home_address = EClass('House')
 #                new_home_address.street = original_home_address.street
 #                new_home_address.city = original_home_address.city
 #                new_object.home_address = new_home_address
 #
 #            # Recursively traverse and populate any contained objects (e.g., if the model has containment references)
 #            for child_ref in original_object.eClass.eAllContainments:
 #                original_children = getattr(original_object, child_ref.name)
 #                new_children = getattr(new_object, child_ref.name)
 #
 #                if isinstance(original_children, list) and isinstance(new_children, list):
 #                    for original_child in original_children:
 #                        new_child = child_ref.eType()
 #                        self.traverse_and_populate(original_child, new_child)
 #                        new_children.append(new_child)