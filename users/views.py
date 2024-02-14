from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from django.contrib.auth import authenticate
from users.serializers import LogInSerializer,DaasSerializer,UpdateDaasSerializer,UserSerializer,ValidUserSerializer
from users.handler import DaasTokenAuthentication
from daas.permissions import OnlyAdmin,OnlyOwner,OnlyMetaAdmin
from rest_framework.viewsets import ModelViewSet
from services.keycloak import Keycloak
from services.syslog import SysLog
from django.utils.translation import gettext as _
from users.token import CustomToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import filters
from rest_framework.permissions import OR
from services.desktop import Desktop
from daas.pagination import CustomPagination
from users.models import Daas,Users
from config.models import Config
from utils.fuctions import get_client_ip_address
from django.contrib.auth import login
import copy
import os
import subprocess
import datetime
import traceback


logger = SysLog().logger

class LogInView(APIView):
    
    throttle_scope = "login"
    
    def post(self,request):
        data = request.data
        serializer_data = LogInSerializer(data=data)
        ip_address = str(get_client_ip_address(request))
        if serializer_data.is_valid():
            valid_datas = serializer_data.validated_data
            email = str(valid_datas['email']).lower()
            user_password = valid_datas['password']
            try:
                authenticator = Keycloak()
                is_valid_user = authenticator.is_valid_user(email,user_password)
                if is_valid_user:
                    logger.info(f"user with email: {email} logged in from ip: {ip_address}")
                    config = Config.objects.all().last()
                    daas = Daas.objects.filter(email__iexact=email).last()
                    if daas:
                        daas_configs = daas.daas_configs
                        usage_in_minute = daas.usage_in_minute
                        forbidden_upload_files = daas.forbidden_upload_files
                        forbidden_download_files = daas.forbidden_download_files
                        extra_allowed_upload_files = daas.extra_allowed_upload_files
                        last_login_ip = daas.last_login_ip
                        extra_allowed_download_files = daas.extra_allowed_download_files
                        is_lock = daas.is_lock
                    latest_tag = os.getenv("DAAS_IMAGE_VERSION")
                    if daas and daas.exceeded_usage == False:
                        if daas.is_running:
                            last_uptime = daas.last_uptime
                            now = datetime.datetime.now()
                            delta_time = now - datetime.timedelta(2*int(os.getenv("CELERY_PERIODIC_TASK_TIME")))
                            if last_uptime > delta_time:
                                if ip_address != daas.last_login_ip:
                                    return Response({'error':_(f"This desktop is using by other user!!")},status=status.HTTP_400_BAD_REQUEST)
                        if daas.is_lock:
                            return Response({"error": _("your account is locked!")},status=status.HTTP_400_BAD_REQUEST)
                        refresh_token = str(CustomToken.for_user(daas))
                        access_token = str(CustomToken.for_user(daas).access_token)
                        http_port = daas.http_port
                        container_id = daas.container_id
                        tag = Desktop().get_tag_of_container(container_id)
                        if tag == latest_tag:
                            Desktop().run_container_by_container_id(container_id)
                        else:
                            Desktop().update_daas_version(container_id,email,user_password)
                            container_id = Desktop().get_container_id_from_port(http_port) 
                            daas.container_id = container_id
                            daas.daas_configs = daas_configs
                            daas.usage_in_minute = usage_in_minute
                            daas.forbidden_upload_files = forbidden_upload_files
                            daas.forbidden_download_files = forbidden_download_files
                            daas.extra_allowed_upload_files = extra_allowed_upload_files
                            daas.extra_allowed_download_files = extra_allowed_download_files
                            daas.last_login_ip = last_login_ip
                            daas.is_lock = is_lock
                        daas.is_running=True
                        daas.last_uptime=datetime.datetime.now()
                        daas.daas_version = latest_tag
                        daas.last_login_ip = ip_address
                        daas.save()
                        return Response({"http":f"http://{config.daas_provider_baseurl}:{daas.http_port}","https":f"https://{config.daas_provider_baseurl}:{daas.https_port}","refresh_token":refresh_token,"access_token":access_token},status.HTTP_200_OK)
                    elif daas and daas.exceeded_usage:
                        return Response({"error":_("you reach your time limit!")},status=status.HTTP_403_FORBIDDEN)
                    else:
                        credential_env = os.getenv("DAAS_FORCE_CREDENTIAL")
                        if credential_env.lower()=="false":
                            force_credential = False
                        else:
                            force_credential = True
                        if force_credential:
                            http_port,https_port = Desktop().create_daas_with_credential(email,user_password)
                        else:
                            http_port,https_port = Desktop().create_daas_without_crediential()
                        container_id = Desktop().get_container_id_from_port(http_port) 
                        daas = Daas.objects.create(email=email,http_port=http_port,https_port=https_port,is_running=True,last_uptime=datetime.datetime.now(),container_id=container_id,daas_version=latest_tag,last_login_ip=ip_address)
                        refresh_token = str(CustomToken.for_user(daas))
                        access_token = str(CustomToken.for_user(daas).access_token)
                        return Response({"http":f"http://{config.daas_provider_baseurl}:{http_port}","https":f"https://{config.daas_provider_baseurl}:{https_port}","refresh_token":refresh_token,"access_token":access_token},status.HTTP_200_OK)
                else:
                    try:
                        user = authenticate(request,email=email,password=user_password)
                        if user and user.is_superuser:
                            logger.info(f"an admin with email: {email} logged in from ip: {ip_address}")
                            user = Users.objects.get(email=email)
                            refresh_token = str(RefreshToken.for_user(user))
                            access_token = str(RefreshToken.for_user(user).access_token)
                            login(request,user)
                            return Response({"info":_("successfull"),"access_token":access_token,"refresh_token":refresh_token},status=status.HTTP_200_OK)
                        else:
                            return Response({"error":_("invalid username or password")},status=status.HTTP_400_BAD_REQUEST)
                    except:
                        logger.error(traceback.format_exc())
                        return Response({"error":_("internal server error")},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except:
                
                # used when no authentication set or handle
                try:
                    user = authenticate(request,email=email,password=user_password)
                    if user and user.is_superuser:
                        logger.info(f"an admin with email: {email} logged in from ip: {ip_address}")
                        user = Users.objects.get(email=email)
                        refresh_token = str(RefreshToken.for_user(user))
                        access_token = str(RefreshToken.for_user(user).access_token)
                        login(request,user)
                        return Response({"info":_("successfull"),"access_token":access_token,"refresh_token":refresh_token},status=status.HTTP_200_OK)
                    else:
                        return Response({"error":_("invalid username or password")},status=status.HTTP_400_BAD_REQUEST)
                except:
                    logger.error(traceback.format_exc())
                    return Response({"error":_("internal server error")},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response(serializer_data.errors,status=status.HTTP_400_BAD_REQUEST)
    

class DaasView(ModelViewSet):
    
    queryset=Daas.objects.all()
    serializer_class=DaasSerializer
    filter_backends = [filters.SearchFilter]
    authentication_classes=(DaasTokenAuthentication,)
    search_fields = ['email',]
    pagination_class = CustomPagination
    http_method_name=['get','patch','delete','option','head']
    
    def get_serializer_class(self):
        if self.action == 'update' or self.action == 'partial_update':
            return UpdateDaasSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        if self.action == 'retrieve':
            return[OR(OnlyOwner(),OnlyAdmin())]
        else:
            return[OnlyAdmin()]
    
    def update(self, request, *args, **kwargs):
        try:
            daas = self.get_object()
            data = request.data
            user = request.user
            ser_data = UpdateDaasSerializer(instance=daas,data=data)
            if ser_data.is_valid():
                ser_data.save()
                logger.info(f"user : {user.email} update daas for user: {daas.email} with data {data}")
                return Response({"info":_("successfull")},status=status.HTTP_202_ACCEPTED)
            else:
                return Response(ser_data.errors,status=status.HTTP_400_BAD_REQUEST)
        except:
            logger.error(traceback.format_exc())
            return Response({"error":_("invalid data passed")},status=status.HTTP_400_BAD_REQUEST)
        
    def destroy(self, request,pk,*args, **kwargs):
        daas = self.get_object()
        user = request.user
        if daas:
            container_id = daas.container_id
            logger.info(f"user : {user.email} destroy daas for user: {daas.email}")
            subprocess.call(['docker','stop',f'{container_id}'])
            subprocess.call(['docker','rm',f'{container_id}'])
        return super().destroy(request, *args, **kwargs)
        
class Profile(ModelViewSet):
    
    authentication_classes = (DaasTokenAuthentication,)
    permission_classes = [OnlyOwner|OnlyAdmin]
    
    def get(self,request):
        requester = request.user
        if isinstance(requester,Daas):
            if requester.is_lock:
                return Response({"error":_("you are blocked!")},status=status.HTTP_401_UNAUTHORIZED)
            ser_data = DaasSerializer(requester)
        elif isinstance(requester,Users):
            ser_data = UserSerializer(requester)
        else:
            return Response({"error":_("invalid data passed")},status=status.HTTP_400_BAD_REQUEST)
        return Response(ser_data.data,status=status.HTTP_200_OK)
        

class UpdateUsage(ModelViewSet):
    authentication_classes = (DaasTokenAuthentication,)
    permission_classes = [OnlyOwner,]
    
    def get(self,request):
        try:
            daas = request.user
            if daas and daas and daas.is_running:
                if daas.is_lock:
                    return Response({"error":_("you are blocked!")},status=status.HTTP_401_UNAUTHORIZED)
                last_uptime = datetime.datetime.timestamp(daas.last_uptime)
                now = datetime.datetime.now().timestamp()
                usage = (now - last_uptime)/60
                last_usage = daas.usage_in_minute
                daas.usage_in_minute = last_usage+usage 
                daas.last_uptime = datetime.datetime.now()
                daas.save()
                return Response({"info":_("successfully update")},status=status.HTTP_200_OK)
            else:
                return Response({"error":_("you can't update usage of down desktop!")},status=status.HTTP_401_UNAUTHORIZED)
        except:
            logger.error(traceback.format_exc())
            return Response({"error":_("internal server error")},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
class ResetUsage(ModelViewSet):
    queryset = Daas.objects.all()
    authentication_classes = (DaasTokenAuthentication,)
    permission_classes = (OnlyAdmin,)
    http_method_names = ['get',]
    serializer_class = DaasSerializer
    
    
    def list(self, request, *args, **kwargs):
        user = request.user
        logger.info(f"user: {user.email} restart all usage of daases")
        daases = self.get_queryset()
        for daas in daases:
            daas.usage_in_minute = 0
            daas.exceeded_usage = False
            daas.save()
            return Response({"info":_("reset successfully")})
    
    def retrieve(self, request, *args, **kwargs):
        user = request.user
        daas = self.get_object()
        daas.usage_in_minute = 0
        daas.exceeded_usage = False
        daas.save()
        logger.info(f"user: {user.email} restart usage of user's daas with email {daas.email}")
        return Response({"info":_("reset successfully")})
    
        
class IsValidUser(APIView):
    def post(self,request):
        try:
            data = request.data
            ser_data = ValidUserSerializer(data=data)
            if ser_data.is_valid():
                valid_datas = ser_data.validated_data
                email = valid_datas['email']
                user_password = valid_datas['password']
                authenticator = Keycloak()
                is_valid_user = authenticator.is_valid_user(email,user_password)
                return Response({"info":is_valid_user},status=status.HTTP_200_OK)
            else:
                return Response(ser_data.errors,status=status.HTTP_400_BAD_REQUEST)
        except:
            logger.info(traceback.format_exc())
            return Response({"error":_("internal server error")})
        
        
class UsersView(ModelViewSet):
    
    queryset=Users.objects.filter(is_superuser=True)
    serializer_class = UserSerializer
    permission_classes = [OnlyMetaAdmin]
    authentication_classes = (DaasTokenAuthentication,)
    filter_backends = [filters.SearchFilter]
    search_fields = ['email','username']
    pagination_class = CustomPagination
    
    def create(self, request, *args, **kwargs):
        data = copy.deepcopy(request.data)
        data.pop("password")
        user = request.user
        logger.info(f"{user.email} create superuser with data {data}")
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        data = copy.deepcopy(request.data)
        obj = self.get_object()
        logger.info(f"user: {request.user.email} update admin with email {obj.email} and data: {data}")
        return super().update(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        serializer.save(is_superuser=True)
        
    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        if request.user.email == obj.email:
            return Response({"error":_("you can't delete yourself!")},status=status.HTTP_400_BAD_REQUEST)
        logger.info(f"user: {request.user.email} delete admin with email {obj.email}")
        return super().destroy(request, *args, **kwargs)
    
class LockRequestView(ModelViewSet):
    queryset = Daas.objects.all()
    authentication_classes = (DaasTokenAuthentication,)
    http_method_names = ['get']
    
    def list(self,request):
        daas = request.user
        daas.is_lock = True
        Desktop().stop_daas_from_port(daas.http_port)
        daas.save()
        logger.info(f"daas with email : {daas.email} locked!")
        return Response({"info":_("locked account successfully")})
    
    def retrieve(self, request, *args, **kwargs):
        return Response({"error":_("can't lock account with given id")})
    

# class DeleteAllDesktops(ModelViewSet):
#     queryset = Daas.objects.all()
#     authentication_classes = (DaasTokenAuthentication,)
#     permission_classes = [OnlyMetaAdmin,]
#     http_method_names = ['get']
    
#     def list(self, request, *args, **kwargs):
#         Desktop().delete_all_containers()
#         daases = Daas.objects.all().delete()
#         return Response({"info":_("deleted succesfully")})
    
#     def retrieve(self, request, *args, **kwargs):
#         return Response({"error":_("retrieve method not allowed")})
    