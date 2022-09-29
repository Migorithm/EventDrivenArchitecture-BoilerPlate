from app.bootstrap import Bootstrap
from app.service_layer.unit_of_work import SqlAlchemyView

BOOTSTRAP = Bootstrap(start_orm=False)


def get_messagebus():
    return BOOTSTRAP()


def get_view():
    return SqlAlchemyView()
