from .auth import register_view, login_view, logout_view
from .dashboard import home
from .jobs import (
    job_list, create_job, job_detail, job_edit, 
    delete_job, toggle_job_status,hr_pending_requests,hr_approve_request,hr_reject_request,
    hr_schedule_interview
)
from .candidates import (
    apply_for_job, candidate_job_status, withdraw_application, cv_builder,
    job_ranking, application_detail, delete_application, reject_application,
    hr_upload_cv, send_interview_invite, bulk_send_invite,
    talent_pool, invite_candidate, kanban_board, update_application_status,schedule_interview_view,
    quick_move_candidate,create_offer,view_offer,respond_offer
)
from .client import (client_dashboard, client_job_view, client_decision,
    client_create_request,add_questions_view,delete_question,client_edit_request,client_delete_request,
    client_edit_question,client_schedule_interview,client_create_offer
)

from .exam import take_exam