from flask import Flask,jsonify
from flask_cors import CORS
#from flask_jwt_extended import JWTManager
import os
os.chdir(os.path.abspath(os.curdir))
from web.get_student_details import GetStudentDetails
from web.select_all import UpdateJobApplicants
from web.refreshboard import GoogleSheetReader
from flask_restful import Api
from web.bdelogin import BdeLogin
from web.get_job_details import GetJobDetails
from web.resumedownload import DownloadResumes
from web.adms.bdesignup import BdeSignup
from web.companylogin import CompanyLogin
from web.companysignup import CompanySignup
from web.jobsapplied import GetAppliedJobsList
from web.applyforjobs import JobApplication
from web.student.studentsapplied import GetAppliedStudentList
from web.list_openings import ListOpenings
from web.student.studentsignup import StudentSignup
from web.studentlogin import StudentLogin
from web.jobpostings import JobPosting  
from web.update_resume import UpdateResume
from web.student_OTP import StudentVerification
from web.validateOTP import ValidateOTP
import json
import urllib.parse
from pymongo import MongoClient 
from web.adms.manager import ManagerLogin
from web.student.all_student import GetAllStudents
from web.all_resumes import AllResumes
from web.edit_job import EditJob
from web.forgotpwd import ForgotPwd
from web.updatepwd import Updatepassword
from web.student.add_student import Add_Student
from web.student.search_std import Search_student
from web.adms.Admin import SuperAdmin
from web.adms.mentor import Mentors
from web.ats import ATSCheck
from web.all_login import Logins
from web.attend.attends_1 import Attendace
from web.attend.attends_data import AttendData
from web.attend.attends_check import AttendCheck
from web.adms.curriculam import CurriCulum
from web.attend.attends_get import GetAttendance
from web.student.student_locs import StudentsByLocation
from web.schedules import ScheduleBatches
from web.adms.batch_creat import CreateBatch
from web.adms.mentor_curriculum import Mentor_CurriCulum
from web.adms.mentors_stds import ListofStudentsForMentor
from web.student.std_curiculum import StudentsCurriculum
from web.student.std_leave import StudentLeaveRequest
from web.adms.leave_manager import ManagerLeaveupdated
from web.adms.adms_count import AllAdminsCount
from web.student.pro import Profile_pic
from web.server import StdRunCode
from web.attend.batch_attends import GetBatchwiseAttendance
from web.Exam.Testing.tester_login import Testers
from web.student.zoho_add import Add_zoho_Student
from web.student.zoho_invoice import zoho_Invoice
#sandeep
from web.Exam.examiner.upload_questions import UploadQuestions
from web.Exam.examiner.Check_Exam_Satus import  CheckExamStatus
from web.Exam.examiner.get_exam_data import GetExamData
from web.Exam.examiner.day_generate_exam_paper import GenerateExamPaper
from web.Exam.examiner.examiner_exam_batch_reports  import ExaminerBatchReports
from web.Exam.examiner.examiner_exam_daylist import ExaminerExamDayList
from web.Exam.student.get_daily_exams_status import GetAvailableExams
from web.Exam.student.start_exams import StartExam
from web.Exam.student.submission import Submissions
from web.Exam.student.submit_exam import SubmitExam
from web.Exam.student.student_report import StudentExamReports
from web.Exam.Whatsapp_Notify.examreport import ExamReport
from web.Exam.Testing.test_upload_questions import TestUploadQuestions
from web.Exam.Testing.question_crud import Question
from web.Exam.Testing.tester_login import Testers
from web.Exam.Testing.tester_curriculum import TesterCurriculum
from web.Exam.Testing.verify_question import VerifyQuestion
from web.Exam.Testing.testsubmissions import TestSubmission
from web.Exam.Testing.intern_progress_summary import InternProgressSummary

with open('local_config.json', 'r') as config_file:
    config_data = json.load(config_file)

MONGO_CONFIG = config_data['MONGO_CONFIG']
MONGO_CONFIG12 = config_data['MONGO_CONFIG']['url']
print(MONGO_CONFIG12)

class MyFlask(Flask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        uri = MONGO_CONFIG['url']
        
        parsed_uri = urllib.parse.urlparse(uri)
        escaped_username = urllib.parse.quote_plus(parsed_uri.username)
        escaped_password = urllib.parse.quote_plus(parsed_uri.password)

        # Reconstruct URI with escaped username and password
        escaped_uri = uri.replace(parsed_uri.username, escaped_username).replace(parsed_uri.password, escaped_password)

        self.client = MongoClient(escaped_uri)
        self.db = self.client[MONGO_CONFIG['db_name']]
        self.collection = self.db[MONGO_CONFIG['collection_name']]

        self.bde_login_collection = MONGO_CONFIG["BDE_LOGIN"]["collection_name"]
        self.student_collection = MONGO_CONFIG["STUDENT_LOGIN"]["collection_name"]
        self.job_details_collection = MONGO_CONFIG["JOBS"]["collection_name"]
        self.company_login_collection = MONGO_CONFIG["COMPANY"]["collection_name"]
        self.otp_collection = MONGO_CONFIG["OTP_COLLECTION"]["collection_name"]
        self.manager_collection = MONGO_CONFIG["Manager_COLLECTION"]["collection_name"]
        self.admin_collection = MONGO_CONFIG["Admin_COLLECTION"]["collection_name"]
        self.mentor_collection = MONGO_CONFIG["Mentor_COLLECTION"]["collection_name"]
        self.resume_collection = MONGO_CONFIG["Resume_COLLECTION"]["collection_name"]
        self.attendance_collection = MONGO_CONFIG["Attendance"]["collection_name"]
        self.curriculum_collection = MONGO_CONFIG["curriculum"]["collection_name"]
        self.schedule_collection = MONGO_CONFIG["schedule"]["collection_name"]
        self.exam_collection = MONGO_CONFIG["exams"]["collection_name"]
        self.questions_collection = MONGO_CONFIG["questions"]["collection_name"]
        self.batches_collection = MONGO_CONFIG["batches"]["collection_name"]
        self.daily_class_collection = MONGO_CONFIG["daily_classes_data"]["collection_name"]
        self.leave_collection = MONGO_CONFIG["leave_request"]["collection_name"]
        
        self.DASHBOARDSHEET = config_data["DASHBOARD_GSHEET"]["url"]
        self.DASHBOARD_COLLECTION = config_data["DASHBOARD_GSHEET"]["collection"]
        self.SHEET_NAME = config_data["DASHBOARD_GSHEET"]["sheetname"]


    def add_api(self):
        api = Api(self, catch_all_404s=True)
        api.add_resource(
            StudentSignup,
            "/api/v1/signup",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'collection' : self.student_collection
                }
        )
        api.add_resource(
            StudentLogin,
            "/api/v1/studentlogin",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'collection' : self.student_collection
                }
        )
        api.add_resource(
            Profile_pic,
            "/api/v1/pic",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'student_collection': self.student_collection
            }
        )
        api.add_resource(
            BdeSignup,
            "/api/v1/bdesignup",
            resource_class_kwargs = {
                'client' : self.client,
                'db' : "codegnan_product",
                'collection' : self.bde_login_collection,
                'manager_collection':  self.manager_collection,
                'mentor_collection':self.mentor_collection,
                'student_collection':self.student_collection
            }
        )
        api.add_resource(
            BdeLogin,
            "/api/v1/bdelogin",
            resource_class_kwargs = {
                'client' : self.client,
                'db_name' : "codegnan_product",
                'collection' : self.bde_login_collection
            }
        )
        api.add_resource(
            CompanyLogin,
            "/api/v1/companylogin",
            resource_class_kwargs = {
                'client' : self.client,
                'db' : "codegnan_product",
                'collection' : self.company_login_collection
            }
        )
        api.add_resource(
            CompanySignup,
            "/api/v1/companysignup",
            resource_class_kwargs = {
                'client' : self.client,
                'db' : "codegnan_product",
                'collection' : self.company_login_collection
            }
        )
        api.add_resource(
            JobPosting,
            "/api/v1/postjobs",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'collection': self.job_details_collection,
                'student_collection': self.student_collection
            }
        )
        api.add_resource(
            ListOpenings,
            "/api/v1/listopenings",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'collection': self.job_details_collection
            }
        )
        api.add_resource(
            JobApplication,
            "/api/v1/applyforjob",
            resource_class_kwargs = {
                'client' : self.client,
                'db' : "codegnan_product",
                'job_collection': self.job_details_collection,
                'student_collection': self.student_collection
            }
        )
        api.add_resource(
            GetAppliedStudentList,
            "/api/v1/getappliedstudentslist",
            resource_class_kwargs = {
                'client' : self.client,
                'db' : "codegnan_product",
                'job_collection': self.job_details_collection,
                'student_collection': self.student_collection
            }
        )
        api.add_resource(
            GetAppliedJobsList,
            "/api/v1/getappliedjobslist",
            resource_class_kwargs = {
                'client' : self.client,
                'db' : "codegnan_product",
                'job_collection': self.job_details_collection,
                'student_collection': self.student_collection
            }
        )
        api.add_resource(
            DownloadResumes,
            "/api/v1/downloadresume",
            resource_class_kwargs = {
                'client' : self.client,
                'db': "codegnan_product",
                "student_collection": self.student_collection
            }
        )

        api.add_resource(
            UpdateJobApplicants,
            "/api/v1/updatejobapplicants",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'job_collection': self.job_details_collection,
                'student_collection': self.student_collection,
                'bde_collection':self.bde_login_collection
            }
        )
        
        api.add_resource(
            GoogleSheetReader,
            "/api/v1/refreshdashboard",
            resource_class_kwargs = {
            }
        )

        api.add_resource(
            GetStudentDetails,
            "/api/v1/getstudentdetails",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'student_collection': self.student_collection
            }
        )

        api.add_resource(
            GetJobDetails,
            "/api/v1/getjobdetails",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'job_collection': self.job_details_collection
            }
        )
        api.add_resource(
            UpdateResume,
            "/api/v1/updateresume",
            resource_class_kwargs = {
                'client' : self.client, 
                'db': "codegnan_product",
                "student_collection": self.student_collection
            }
        )
        api.add_resource(
            StudentVerification,
            "/api/v1/studentotp",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'otp_collection': self.otp_collection
            }
        )
        api.add_resource(
            ValidateOTP,
            "/api/v1/verifyotp",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'otp_collection': self.otp_collection
            }
        )
        api.add_resource(
            ManagerLogin,
            "/api/v1/manager",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'manager_collection': self.manager_collection,
                'bde_collection':self.bde_login_collection,
                'mentor_collection':self.mentor_collection,
                'student_collection':self.student_collection
            }
        )
        api.add_resource(
            GetAllStudents,
            "/api/v1/allstudents",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'student_collection': self.student_collection
            }
        )
        api.add_resource(
            StudentsByLocation,
            "/api/v1/stdlocations",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'student_collection': self.student_collection
            }
        )
        api.add_resource(
            AllResumes,
            "/api/v1/allresumes",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'student_collection': self.student_collection
            }
        )
        api.add_resource(
            EditJob,
            "/api/v1/editjob",
            resource_class_kwargs = {
                'client' : self.client, 
                'db': "codegnan_product",
                "job_collection": self.job_details_collection
            }
        )
        api.add_resource(
            ForgotPwd,
            "/api/v1/forgotpassword",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'otp_collection': self.otp_collection,
                'std_collection':self.student_collection,
                'manager_collection':  self.manager_collection,
                'bde_collection':self.bde_login_collection,
                'mentor_collection':self.mentor_collection
            }
        )
        api.add_resource(
            Updatepassword,
            "/api/v1/updatepassword",
            resource_class_kwargs = {
                'client' : self.client, 
                'db': "codegnan_product",
                'std_collection':self.student_collection,
                'manager_collection':  self.manager_collection,
                'bde_collection':self.bde_login_collection,
                'mentor_collection':self.mentor_collection
            }
        )
        api.add_resource(
            Add_Student,
            "/api/v1/addstudent",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'collection' : self.student_collection,
                'manager_collection': self.manager_collection,
                'bde_collection':self.bde_login_collection,
                'mentor_collection':self.mentor_collection,
                }
        )
        api.add_resource(
            Search_student,
            "/api/v1/searchstudent",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'std_collection' : self.student_collection,
                'job_collection' : self.job_details_collection,
                 'attendance'   : self.attendance_collection         
                }
        )
        api.add_resource(
            SuperAdmin,
            "/api/v1/admin",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'admin_collection':self.admin_collection
            }
        )
        api.add_resource(
            Mentors,
            "/api/v1/mentor",
            resource_class_kwargs = {
                'client' : self.client,
                'db' : "codegnan_product",
                'manager_collection':  self.manager_collection,
                'bde_collection':self.bde_login_collection,
                'collection':self.mentor_collection,
                'student_collection':self.student_collection
            }
        )
        api.add_resource(
            ATSCheck,
            "/api/v1/atscheck",
            resource_class_kwargs = {
                'client' : self.client,
                'db' : "codegnan_product",
                'collection' : self.resume_collection
            }
        )
        api.add_resource(
            Logins,
            "/api/v1/login",
            resource_class_kwargs={
                'client' : self.client,
                'db_name' : "codegnan_product",
                'manager_collection':  self.manager_collection,
                'bde_collection':self.bde_login_collection,
                'mentor_collection':self.mentor_collection,
                'student_collection':self.student_collection
            }
        )
        api.add_resource(
            Attendace,
            "/api/v1/attend",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'collection' : self.student_collection
                }
        )
        api.add_resource(
            AttendData,
            "/api/v1/attendance",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'collection' : self.attendance_collection
                }
        )
        api.add_resource(
            AttendCheck,
            "/api/v1/attendcheck",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'collection' : self.attendance_collection
                }
        )
        api.add_resource(
            GetAttendance,
            "/api/v1/getattends",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'collection' : self.attendance_collection
                }
        )
        api.add_resource(
            CurriCulum,
            "/api/v1/syllabus",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'collection' : self.curriculum_collection
                }
        )
        api.add_resource(
            ScheduleBatches,
            "/api/v1/schedule",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'schedule_collection' : self.schedule_collection,
                'mentor_collection':self.mentor_collection
                }
        )
        api.add_resource(
            CreateBatch,
            "/api/v1/batches",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'collection' : self.batches_collection
                }
        )
        api.add_resource(
            Mentor_CurriCulum,
            "/api/v1/mentorsyllabus",
            resource_class_kwargs={
                
            }
        )
        api.add_resource(
            ListofStudentsForMentor,
            "/api/v1/mentorstds",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'collection' : self.schedule_collection,
                'student_collection':self.student_collection,
                'mentor_collection':self.mentor_collection,
                'classdata_collection' : self.daily_class_collection
                }
        )
        api.add_resource(
            StudentsCurriculum,
            "/api/v1/stdcurriculum",
            resource_class_kwargs={

            }
        )
        api.add_resource(
            StudentLeaveRequest,
            "/api/v1/stdleave",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'leave_collection' : self.leave_collection
                }
        )
        api.add_resource(
            ManagerLeaveupdated,
            "/api/v1/leaves",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'leave_collection' : self.leave_collection,
                'manager_collection':self.manager_collection
                }
        )
        api.add_resource(
            AllAdminsCount,
            "/api/v1/adminsdata",
            resource_class_kwargs = {
                'client' : self.client,
                'db' : "codegnan_product",
                'mentor_collection' : self.mentor_collection,
                'manager_collection':self.manager_collection,
                "bde_collection":self.bde_login_collection
            }
        ) 
        api.add_resource(
            GetBatchwiseAttendance,
            "/api/v1/batchwiseattends",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'collection' : self.attendance_collection
                }
        ),

        api.add_resource(
            Add_zoho_Student,
            "/api/v1/zohostudent",
            resource_class_kwargs={
                'client' : self.client,
                'db' : "codegnan_product",
                'collection' : self.student_collection,
                'manager_collection': self.manager_collection,
                'bde_collection':self.bde_login_collection,
                'mentor_collection':self.mentor_collection,
                'batch':self.batches_collection
                } )
        api.add_resource(zoho_Invoice,"/api/v1/zohoinvoice")
        api.add_resource(Testers,"/api/v1/tester")

        api.add_resource(StdRunCode,'/api/v1/runcode')
        api.add_resource(UploadQuestions,"/api/v1/uploadquestions")       
        api.add_resource(CheckExamStatus, "/api/v1/check-exam-status") 
        api.add_resource(GetExamData, "/api/v1/get-exam-data") 
        api.add_resource(GenerateExamPaper, "/api/v1/generate-exam-paper")
        api.add_resource(ExaminerExamDayList, "/api/v1/exam-day-list")
        api.add_resource(ExaminerBatchReports, "/api/v1/exam-batch-reports") 
        api.add_resource(GetAvailableExams, "/api/v1/get-available-exams")
        api.add_resource(StartExam, "/api/v1/startexam")
        api.add_resource(Submissions, "/api/v1/submissions")
        api.add_resource(SubmitExam, "/api/v1/submit-exam")
        api.add_resource(StudentExamReports, "/api/v1/student-reports")
        api.add_resource(ExamReport, "/api/v1/exam-report")
        #Testing
        api.add_resource(TestUploadQuestions, "/api/v1/test-upload-questions")
        api.add_resource(Question, "/api/v1/question-crud")
        api.add_resource(TesterCurriculum, "/api/v1/tester-curriculum")
        api.add_resource(VerifyQuestion, "/api/v1/verify-question")
        api.add_resource(TestSubmission, "/api/v1/test-submission")
        api.add_resource(InternProgressSummary, "/api/v1/intern-progress-summary")


app = MyFlask(__name__)
# app.config["JWT_SECRET_KEY"] = b'\x912\xa5T\x91(\x0b\x89'
# jwt = JWTManager(app)

app.add_api()

CORS(app,support_credentials=True)
if __name__ == '__main__':
    app.run()
# "url": "mongodb+srv://codegnandevelopment:codegnandevelopment@cluster0.yy9e5fa.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0",
# Locally url:"mongodb+srv://datta:datta@cluster0.9ek0btm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
#old {"url":"https://docs.google.com/spreadsheets/d/1waUnCAzLnLbiKABbGNppDZ6Vj-vpV0mNy-ypLp1yZ2Q/edit?gid=0#gid=0"}
# podman build -t codegnan-app .
# podman run -d -p 5000:5000 --name python-container codegnan-app