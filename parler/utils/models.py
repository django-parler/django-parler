from django.db.models import ForeignKey

# A copy of django.db.models._get_foreign_key():

def get_foreign_key(parent_model, model, fk_name=None, can_fail=False):
    opts = model._meta
    if fk_name:
        fks_to_parent = [f for f in opts.fields if f.name == fk_name]
        if len(fks_to_parent) == 1:
            fk = fks_to_parent[0]
            if not isinstance(fk, ForeignKey) or \
                    (fk.rel.to != parent_model and
                     fk.rel.to not in parent_model._meta.get_parent_list()):
                raise Exception("fk_name '%s' is not a ForeignKey to %s" % (fk_name, parent_model))
        elif len(fks_to_parent) == 0:
            raise Exception("%s has no field named '%s'" % (model, fk_name))
    else:
        # Try to discover what the ForeignKey from model to parent_model is
        fks_to_parent = [
            f for f in opts.fields
            if isinstance(f, ForeignKey)
            and (f.rel.to == parent_model
                or f.rel.to in parent_model._meta.get_parent_list())
        ]
        if len(fks_to_parent) == 1:
            fk = fks_to_parent[0]
        elif len(fks_to_parent) == 0:
            if can_fail:
                return
            raise Exception("%s has no ForeignKey to %s" % (model, parent_model))
        else:
            raise Exception("%s has more than 1 ForeignKey to %s" % (model, parent_model))
    return fk
