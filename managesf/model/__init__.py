#
# Copyright (c) 2015 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from pecan import conf  # noqa
from sqlalchemy import create_engine, Column, String, Integer, exc
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()
engine = None


def row2dict(row):
    ret = {}
    for column in row.__table__.columns:
        ret[column.name] = str(getattr(row, column.name))
    return ret


class User(Base):
    __tablename__ = 'users'
    username = Column(String(), primary_key=True)
    fullname = Column(String(), nullable=False)
    email = Column(String(), nullable=False)
    hashed_password = Column(String(), nullable=False)
    sshkey = Column(String(), nullable=True)


class SFUser(Base):
    __tablename__ = 'SF_USERS'
    id = Column(Integer(), primary_key=True)
    username = Column(String(), nullable=False)
    fullname = Column(String(), nullable=True)
    email = Column(String(), nullable=False)
    cauth_id = Column(Integer(), nullable=False)


class SFUserCRUD:
    def get(self, id=None, username=None, email=None,
            fullname=None, cauth_id=None):
        session = start_session()
        if (id or username or email or fullname or cauth_id):
            filtering = {}
            if id:
                filtering['id'] = id
            if username:
                filtering['username'] = username
            if email:
                filtering['email'] = email
            if fullname:
                filtering['fullname'] = fullname
            if cauth_id:
                filtering['cauth_id'] = cauth_id
            try:
                ret = session.query(SFUser).filter_by(**filtering).one()
                return row2dict(ret)
            except MultipleResultsFound:
                # TODO(mhu) find a better Error
                raise KeyError('search returned more than one result')
            except NoResultFound:
                return {}
        else:
            # all()
            return [row2dict(ret) for ret in session.query(SFUser)]

    def update(self, id, username=None, email=None,
               fullname=None, cauth_id=None):
        session = start_session()
        try:
            ret = session.query(SFUser).filter_by(id=id).one()
            if username:
                ret.username = username
            if email:
                ret.email = email
            if fullname:
                ret.fullname = fullname
            if cauth_id:
                ret.cauth_id = cauth_id
            session.commit()
        except MultipleResultsFound:
            # TODO(mhu) find a better Error
            raise KeyError('search returned more than one result')
        except NoResultFound:
            # TODO(mhu) this should probably be logged somewhere
            return

    def create(self, username, email,
               fullname, cauth_id=None):
        session = start_session()
        if username and email and fullname:
            # assign a dummy value in case we lack the information
            # as is likely to happen when migrating from a previous version.
            # TODO(mhu) remove these for version n+2
            cid = cauth_id or -1
            user = SFUser(username=username,
                          email=email,
                          fullname=fullname,
                          cauth_id=cid)
            session.add(user)
            session.commit()
            return user.id
        else:
            msg = "Missing info required for user creation: %s|%s|%s"
            raise KeyError(msg % (username, email, fullname))

    def delete(self, id=None, username=None, email=None,
               fullname=None, cauth_id=None):
        session = start_session()
        filtering = {}
        if id:
            filtering['id'] = id
        if username:
            filtering['username'] = username
        if email:
            filtering['email'] = email
        if fullname:
            filtering['fullname'] = fullname
        if cauth_id:
            filtering['cauth_id'] = cauth_id
        try:
            ret = session.query(SFUser).filter_by(**filtering).one()
            session.delete(ret)
            session.commit()
            return True
        except MultipleResultsFound:
            # TODO(mhu) find a better Error
            raise KeyError('search returned more than one result')
        except NoResultFound:
            return False


def init_model():
    c = dict(conf.sqlalchemy)
    url = c.pop('url')
    globals()['engine'] = create_engine(url, **c)
    Base.metadata.create_all(engine)


def start_session():
    Base.metadata.bind = engine
    dbsession = sessionmaker(bind=engine)
    session = dbsession()
    return session


def add_user(user):
    """ Add a user in the database
        return Boolean
    """
    session = start_session()
    u = User(**user)
    session.add(u)
    try:
        session.commit()
        return True, None
    except exc.IntegrityError as e:
        return False, e.message


def get_user(username):
    """ Fetch a user by its username
        return user dict or False if not found
    """
    session = start_session()
    try:
        ret = session.query(User).filter(User.username == username).one()
    except NoResultFound:
        return False
    return row2dict(ret)


def delete_user(username):
    """ Delete a user by its username
        return True if deleted or False if not found
    """
    session = start_session()
    ret = session.query(User).filter(User.username == username).delete()
    session.commit()
    return bool(ret)


def update_user(username, infos):
    """ Update a user by its username
        arg infos: Dict
        return True if deleted or False if not found
    """
    session = start_session()
    ret = session.query(User).filter(User.username == username).update(infos)
    session.commit()
    return bool(ret)
