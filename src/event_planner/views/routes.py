from .. import db, models, app
from flask import flash, redirect, abort, render_template, url_for, request
from datetime import date as dt, time
from datetime import datetime
from dateutil import parser
from .. import utils
from . import forms
from functools import reduce

empty_form = forms.EventForm.default_form()
empty_dateform = forms.DateForm.default_form()
empty_participantform = forms.ParticipantForm.default_form()

@app.route("/")
def index():
    """GET - Default view of all events"""
    events = models.Event.query.all()

    return render_template('index.html', events=events)

@app.route("/new", methods=['GET'])
def new_get():
    """GET - New event form"""
    return render_template('new.html', form=empty_form())

@app.route("/new", methods=['POST'])
def new_post():
    """Creates a new event and commits it to the db"""

    form = empty_form(request.form)

    if form.validate():
        event = models.Event(
            form.eventname.data,
            form.eventdescription.data
        )
        db.session.add(event)

        admin = models.Participant(
            form.adminname.data,
            event,
            True
        )
        db.session.add(admin)

        dateslot = models.Dateslot(
            form.date.data,
            admin
        )
        db.session.add(dateslot)

        for timeslot in form.timeslots:
            val = form["slot_%s" % timeslot.strftime("%H%M")].data[0]
            if val is True:
                t = models.Timeslot(timeslot, dateslot)
                db.session.add(t)
        # for entry in form.tasks.entries:
        #     task = models.Task(entry.data['task'], False, None, event.id)
        #     db.session.add(task)
        db.session.commit()

        return redirect(url_for("index"))
    else:
        return render_template("new.html", form=form), 400

@app.route("/event/<event_id>", methods=['GET'])
def show_event_get(event_id):
    """ GET - user view of event"""

    #Get event by ID from DB and send to event view
    event = get_event(event_id) or abort(404)
    event_admin = list(filter(lambda x: x.is_admin == True, event.participants))
    event_dateslots = filter((lambda d : d.timeslots ), event_admin[0].dateslots)
    event_timeslots = reduce((lambda x,y : x + y), map((lambda x : x.timeslots), event_dateslots), [])
    event_times = map((lambda x : x.time), event_timeslots)

    participants = list(event.participants)

    form_type = forms.ParticipantForm.default_form(event_times)
    form = form_type()

    return render_template('event_view.html', form=form, event=event, admin=event_admin, participants=participants, event_dateslots=event_dateslots)


@app.route("/event/<event_id>", methods=['POST'])
def show_event_post(event_id=None):
    """ POST - user adds participation """

    #Get event info
    event = get_event(event_id)
    admin_timeslots = event.admin.timeslots
    timeslot_times = [timeslot.time for timeslot in admin_timeslots]
    form_type = forms.ParticipantForm.default_form(timeslot_times)
    form = form_type(request.form)

    if form.validate():
        participant = models.Participant(form.participantname.data, event, False)
        db.session.add(participant)

        for slot in form.timeslots:
             val = form["slot_%s" % slot.strftime("%H%M")].data[0]
             if val is True:
                t = models.Timeslot(slot, participant)
                db.session.add(t)

        db.session.commit()

    return redirect(url_for('show_event_get', event_id=event_id))



@app.route("/event/<event_id>/newtask", methods=['GET'])
def new_task_get(event_id):
    """GET - New event task form"""
    return render_template('newtask.html', form=forms.TaskForm())


@app.route("/event/<event_id>/newtask", methods=['POST'])
def new_task_post(event_id):
    """Creates a new event task and commits it to the db"""

    form = forms.TaskForm(request.form)
    if form.validate():
        task = models.Task(
            form.name.data,
            False,
            None,
            event_id)
        db.session.add(task)
        db.session.commit()
        return redirect(url_for('show_event_get', event_id=event_id))
    else:
        return render_template("newtask.html", form=form, event_id=event_id), 400


@app.route("/event/<event_id>/respond", methods=['GET'])
def new_response(event_id):
    event = get_event(event_id) or abort(404)
    event_admin = list(filter(lambda x: x.is_admin == True, event.participants))

    event_dateslots = filter((lambda d : d.timeslots ), event_admin[0].dateslots)

    date = request.args.get('date')

    if 'date' in locals() and date != None:

        specific_dateslots = filter((lambda x : x.date == parser.parse(request.args.get('date')).date()), event_dateslots)
        date_timeslots = reduce((lambda x,y : x + y), map((lambda x : x.timeslots), specific_dateslots), [])
        event_times = map((lambda x : x.time), date_timeslots)

        form_type = forms.ParticipantForm.default_form(event_times)
        form = form_type()

        return render_template('respond.html', form=form, event_timeslots=date_timeslots, date=date)
    else:
        return render_template('respond_dates.html', event=event, dateslots=event_dateslots)


@app.route("/event/<event_id>/respond", methods=['POST'])
def create_response(event_id):

    event = get_event(event_id)
    event_admin = list(filter(lambda x: x.is_admin == True, event.participants))

    event_dateslots = filter((lambda d : d.timeslots ), event_admin[0].dateslots)
    event_timeslots = reduce((lambda x,y : x + y), map((lambda x : x.timeslots), event_dateslots), [])
    event_times = map((lambda x : x.time), event_timeslots)

    form_type = forms.ParticipantForm.default_form(event_times)
    form = form_type(request.form)

    if True:
        participant = models.Participant(form.participantname.data, event, False)

        dateslot = models.Dateslot(
            parser.parse(request.args.get('date')).date(),
            participant
        )
        db.session.add(dateslot)

        for timeslot in form.timeslots:
            form_time = form["slot_%s" % timeslot.strftime("%H%M")].data + [False]
            val = form_time[0]
            if val is True:
                t = models.Timeslot(timeslot, dateslot)
                db.session.add(t)

        # form
        db.session.commit()

        return redirect(url_for('show_event_get', event_id=event_id))
    else:
        return render_template("respond.html", form=form, event=event,  event_timeslots=event_timeslots, dateslots=event_dateslots), 400

@app.route("/event/<event_id>/respondtask", methods=['GET'])
def new_task_response(event_id):
    event = get_event(event_id) or abort(404)
    
    form = forms.ParticipantTaskForm(request.form)
    event_tasks = []
    for a in event.tasks:
        if a.is_assigned == False:
            event_tasks.append((a.id, a.task))

    form.participanttasks.choices = event_tasks
                            
    return render_template('respondtask.html', form=form)

@app.route("/event/<event_id>/respondtask", methods=['POST'])
def create_task_response(event_id):

    event = get_event(event_id)
    form = forms.ParticipantTaskForm(request.form)

        
    if True: #form.validate()        
        participant = models.Participant(
            form.participantname.data,
            event,
            False
        )
        db.session.add(participant)
        db.session.flush()
        
        task = models.Task.query.filter_by(event_id = event_id, id=form.participanttasks.data).first()
        task.part_id = participant.id
        task.is_assigned = True

        db.session.commit()
        
        return redirect(url_for('show_event_get', event_id=event_id))
    else:
        return render_template("respondtask.html", form=form, event=event), 400

@app.route("/event/<event_id>/new_dateslot", methods=['GET'])
def new_res(event_id):
    return render_template('new_dateslot.html', form=empty_dateform())

@app.route("/event/<event_id>/new_dateslot", methods=['POST'])
def create_dateslot(event_id):

    event = get_event(event_id)
    form = empty_dateform(request.form)
    admin = event.admin

    if form.validate():
        dateslot = models.Dateslot(
            form.date.data,
            admin
        )
        db.session.add(dateslot)

        for timeslot in form.timeslots:
            val = form["slot_%s" % timeslot.strftime("%H%M")].data[0]
            if val is True:
                t = models.Timeslot(timeslot, dateslot)
                db.session.add(t)
        db.session.commit()
        
        if form.submit.data:
            return redirect(url_for("index"))
        else:
            return render_template("new_dateslot.html", form=form), 400
    else:
        return render_template("new_dateslot.html", form=form), 400


def get_event(id):
    """Utility function to get the first event matching id or None"""
    return models.Event.query.filter(models.Event.id == id).first()
