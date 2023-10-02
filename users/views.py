from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from django.contrib.auth import authenticate
from users.serializers import LogInSerializer,DaasSerializer,UpdateDaasSerializer,UserSerializer
from users.handler import DaasTokenAuthentication
from daas.permissions import OnlyAdmin,OnlyOwner
from rest_framework.viewsets import ModelViewSet
from services.keycloak import Keycloak
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
import subprocess
import datetime
import logging 
import traceback
import logging

logging.basicConfig(level=logging.INFO)

class LogInView(APIView):
    
    def post(self,request):
        data = request.data
        serializer_data = LogInSerializer(data=data)
        if serializer_data.is_valid():
            valid_datas = serializer_data.validated_data
            is_admin = valid_datas['is_admin']
            email = valid_datas['email']
            user_password = valid_datas['password']
            if not is_admin:
                authenticator = Keycloak()
                is_valid_user = authenticator.is_valid_user(email,user_password)
                if is_valid_user:
                    ip_address = get_client_ip_address(request)
                    logging.info(f"user with email: {email} logged in from ip: {ip_address}")
                    config = Config.objects.all().last()
                    daas = Daas.objects.filter(email=email).last()
                    if daas:
                        refresh_token = str(CustomToken.for_user(daas))
                        access_token = str(CustomToken.for_user(daas).access_token)
                        http_port = daas.http_port
                        Desktop().run_container_by_port(http_port)
                        daas.is_running=True
                        daas.last_uptime=datetime.datetime.now()
                        daas.save()
                        return Response({"http":f"http://{config.daas_provider_baseurl}:{daas.http_port}","https":f"https://{config.daas_provider_baseurl}:{daas.https_port}","refresh_token":refresh_token,"access_token":access_token},status.HTTP_200_OK)
                    else:
                        http_port,https_port = Desktop().create_daas(email,user_password)
                        daas = Daas.objects.create(email=email,http_port=http_port,https_port=https_port,is_running=True,last_uptime=datetime.datetime.now())
                        refresh_token = str(CustomToken.for_user(daas))
                        access_token = str(CustomToken.for_user(daas).access_token)
                        return Response({"http":f"http://{config.daas_provider_baseurl}:{http_port}","https":f"https://{config.daas_provider_baseurl}:{https_port}","refresh_token":refresh_token,"access_token":access_token},status.HTTP_200_OK)
                else:
                    return Response({"error":_("invalid user")},status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    user = authenticate(request,email=email,password=user_password)
                    if user.is_superuser:
                        user = Users.objects.get(email=email)
                        refresh_token = str(RefreshToken.for_user(user))
                        access_token = str(RefreshToken.for_user(user).access_token)
                        return Response({"info":_("successfull"),"access_token":access_token,"refresh_token":refresh_token},status=status.HTTP_200_OK)
                    else:
                        return Response({"error":_("you are not admin")},status=status.HTTP_400_BAD_REQUEST)
                except:
                    logging.error(traceback.format_exc())
                    return Response({"error":_("invalid username or password")},status=status.HTTP_400_BAD_REQUEST)
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
            ser_data = UpdateDaasSerializer(instance=daas,data=data)
            if ser_data.is_valid():
                ser_data.save()
                return Response({"info":_("successfull")},status=status.HTTP_202_ACCEPTED)
            else:
                return Response(ser_data.errors,status=status.HTTP_400_BAD_REQUEST)
        except:
            logging.error(traceback.format_exc())
            return Response({"error":_("invalid data passed")},status=status.HTTP_400_BAD_REQUEST)
        
    def destroy(self, request,pk,*args, **kwargs):
        daas = self.get_object()
        if daas:
            http = daas.http_port
            result = subprocess.check_output(['docker','ps','--filter',f"publish={http}",'--format','{{.ID}}'])
            container_id = str(result.strip().decode('utf-8'))
            subprocess.call(['docker','stop',f'{container_id}'])
            subprocess.call(['docker','rm',f'{container_id}'])
        return super().destroy(request, *args, **kwargs)
        
        
class Profile(ModelViewSet):
    
    authentication_classes = (DaasTokenAuthentication,)
    permission_classes = [OnlyOwner|OnlyAdmin]
    
    def get(self,request):
        requester = request.user
        if isinstance(requester,Daas):
            ser_data = DaasSerializer(requester)
        elif isinstance(requester,Users):
            ser_data = UserSerializer(requester)
        return Response(ser_data.data,status=status.HTTP_200_OK)
        

class UpdateUsage(ModelViewSet):
    authentication_classes = (DaasTokenAuthentication,)
    permission_classes = [OnlyOwner,]
    
    def get(self,request):
        try:
            daas = request.user
            if daas.is_running:
                last_uptime = datetime.datetime.timestamp(daas.last_uptime)
                now = datetime.datetime.now().timestamp()
                usage = (now - last_uptime)/60
                last_usage = daas.usage_in_minute
                daas.usage_in_minute = last_usage+usage 
                daas.last_uptime = datetime.datetime.now()
                daas.save()
                return Response({"info":_("successfully update")},status=status.HTTP_200_OK)
            else:
                return Response({"error":_("you can't update usage of down desktop!")})
        except:
            logging.error(traceback.format_exc())
            return Response({"error":_("internal server error")},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        