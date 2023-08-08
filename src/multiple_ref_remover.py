from datetime import datetime

from pyecore.resources import ResourceSet, URI
from pyecore.ecore import EClass, EReference, EObject, EString, EPackage


def create_mediator_eclass(ref_pairs, package, root):
    eclass1 = ref_pairs[0]
    eclass2 = ref_pairs[1]
    references = ref_pairs[2]

    for ref_pair in references:
        mediator_eclass = EClass(name=f"{eclass1.name[:2]}_{ref_pair.name}_Mediator_{eclass2.name[:2]}")

        # Add mediator EClass to the package
        package.eClassifiers.append(mediator_eclass)

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


def find_referencing_pairs(eclasses):
    referencing_pairs = []
    for eclass1 in eclasses:
        for eclass2 in eclasses:
            # if not_seen_classes(eclass1, eclass2, referencing_pairs):
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
                    if not check_seen_ref(e_opp_refs, referencing_pairs):
                        referencing_pairs.append((eclass1, eclass2, references_in_between))
                        print("eclass1:", eclass1, "eclass2:", eclass2, "\n-> : ", references_in_between)

    return referencing_pairs


def check_seen_ref(e_opp_refs, referencing_pairs):
    temp = False
    for ref_pair in referencing_pairs:
        if ref_pair[0].name is e_opp_refs[0].name:
            if ref_pair[1].name is e_opp_refs[1].name:
                e_opp_set = set(e_opp_refs[2])
                ref_set = set(ref_pair[2])
                temp = e_opp_set.issubset(ref_set)
    return temp


def remove_old_references(referencing_pairs):
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


def main():
    # Load the Ecore file
    ecore_file = '../input/RetalSystem4.ecore'
    resource_set = ResourceSet()
    resource = resource_set.get_resource(URI(ecore_file))
    package = resource.contents[0]  # Assuming there's only one root package in the file

    # Get all EClasses from the package
    eclasses = [element for element in package.eAllContents() if isinstance(element, EClass)]

    root = eclasses[0]
    for e_class in eclasses:
        has_containment_reference = any(
            isinstance(ref, EReference) and ref.containment for ref in e_class.eStructuralFeatures)
        if has_containment_reference:
            root = e_class

    # Find pairs of EClasses with more than one reference to each other
    referencing_pairs = find_referencing_pairs(eclasses)

    # Create and replace references with a mediator EClass
    for ref_pair in referencing_pairs:
        create_mediator_eclass(ref_pair, package, root)

    # Remove old references
    remove_old_references(referencing_pairs)  ##TODO remove the old references in the previous step

    # Print the updated Ecore model
    print(package)

    # Serialize the updated Ecore model to a new Ecore file
    output_file = '../output1/output_file' + datetime.now().strftime(
        '%H%M%S') + '.ecore'  # Change this to the desired output file path
    resource_set = ResourceSet()
    output_resource = resource_set.create_resource(URI(output_file))
    output_resource.append(package)
    output_resource.save()

    # Example usage:
    # Assuming "OriginalModel.xmi" is an XMI file representing the original instance model conforming to the metamodel.
    # remove_pair_references("OriginalModel.xmi")


def remove_pair_references(original_instance_model_file):
    # Step 1: Load the original instance model from the XMI file
    resource_set = ResourceSet()
    resource = resource_set.get_resource(URI(original_instance_model_file))
    original_root_object = resource.contents[0]

    # Step 2: Create a new instance model conforming to the metamodel without pair references
    new_root_object = create_new_instance_model()

    # Step 3: Traverse the original instance model and populate the new model without pair references
    traverse_and_populate(original_root_object, new_root_object)

    # Save the new instance model to a new XMI file
    new_model_file = "new_instance_model.xmi"
    new_resource = resource_set.create_resource(URI(new_model_file))
    new_resource.append(new_root_object)
    new_resource.save()


def create_new_instance_model():
    # Step 2: Create and return a new instance model
    # In this example, let's assume a simple metamodel with two classes: Person and House
    # The Person class has a reference to House (address) and an additional reference (home_address).
    person_package = EPackage('PersonPackage')
    person_package.nsURI = 'http://person'
    person_package.nsPrefix = 'person'

    Person = EClass('Person')
    House = EClass('House')
    person_package.eClassifiers.extend([Person, House])

    # Add the attributes to the classes (e.g., name, street, city)
    name_attr = EString('name')
    street_attr = EString('street')
    city_attr = EString('city')
    Person.eStructuralFeatures.extend([name_attr, EReference('address', House)])
    House.eStructuralFeatures.extend([street_attr, city_attr])

    # Add the additional reference (home_address) to the Person class
    home_address_ref = EReference('home_address', House)
    Person.eStructuralFeatures.append(home_address_ref)

    # Create the root object for the new instance model
    new_root_object = Person()

    return new_root_object


def traverse_and_populate(original_object, new_object):
    # Step 3: Traverse the original instance model, populate the new instance model, and handle pair references

    # In this example, let's assume the original model has instances of the Person class with addresses.
    # We will traverse the original model, create corresponding objects in the new model,
    # and set their attributes and references accordingly.

    if isinstance(original_object, EObject) and isinstance(new_object, EObject):
        # Set the 'name' attribute for the Person
        if 'name' in original_object.eClass.eAllAttributes:
            new_object.name = original_object.name

        # Create a new Address object and set its attributes
        if 'address' in original_object.eClass.eAllReferences:
            original_address = original_object.address
            new_house = EClass('House')
            new_house.street = original_address.street
            new_house.city = original_address.city
            new_object.address = new_house

        # Handle the additional reference (home_address)
        if 'home_address' in original_object.eClass.eAllReferences:
            original_home_address = original_object.home_address
            new_home_address = EClass('House')
            new_home_address.street = original_home_address.street
            new_home_address.city = original_home_address.city
            new_object.home_address = new_home_address

        # Recursively traverse and populate any contained objects (e.g., if the model has containment references)
        for child_ref in original_object.eClass.eAllContainments:
            original_children = getattr(original_object, child_ref.name)
            new_children = getattr(new_object, child_ref.name)

            if isinstance(original_children, list) and isinstance(new_children, list):
                for original_child in original_children:
                    new_child = child_ref.eType()
                    traverse_and_populate(original_child, new_child)
                    new_children.append(new_child)


if __name__ == "__main__":
    main()
