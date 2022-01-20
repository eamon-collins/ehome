from django.shortcuts import render
from django.http import HttpResponse
from django.forms.models import model_to_dict
from .forms import LoginForm

# Create your views here.
def index(request):
	return HttpResponse("This page still under construction")


def login(request):
    form = LoginForm()
    text = " "
    # If we received a GET request instead of a POST request
    if request.method == 'GET':
        # display the login form page
        next = request.GET.get('next') or reverse('index')
        return render(request, 'login.html', {'form':form, 'login':True})

    # Creates a new instance of our login_form and gives it our POST data
    f = LoginForm(request.POST)


    # Check if the form instance is invalid
    if not f.is_valid():
      # Form was bad -- send them back to login page and show them an error
        return render(request, 'login.html', {'ok': False, 'error':'Incorrect form input', 'form':form})

    # Sanitize username and password fields
    username = f.cleaned_data['username']
    password = f.cleaned_data['password']

    try:
    	user = User.objects.get(username = username)
    except User.DoesNotExist:
    	return JsonResponse('ok': False, 'error': "")
 
    if not hashers.check_password(password, user.passhash):
        return _error_response(request, 'Incorrect password')

    while (True):
        authenticator = hmac.new(
            key=settings.SECRET_KEY.encode('utf-8'),
            msg=os.urandom(32),
            digestmod='sha256',
        ).hexdigest()
        try:
            Authenticator.objects.get(authenticator=authenticator)
        except Authenticator.DoesNotExist:
            break

    try:
        Authenticator.objects.get(user_id=user).delete()
        auth = Authenticator.objects.create(user_id=user, authenticator=authenticator)
    except:
        auth = Authenticator.objects.create(user_id=user, authenticator=authenticator)

    auth.save()
    auth = model_to_dict(auth)


    # Ge t next page
    nextpage = f.cleaned_data.get('next') or reverse('index')

    # Send validated information to our experience layer
    data = {'username':username, 'password':password}
    resp = requests.post('http://exp-api:8000/v1/api/login/', data)

    struct = {}
    try:
        dataform = str(resp).strip("'<>() ").replace('\'', '\"')
        struct = json.loads(dataform)
        text = struct["results"]
    except:
        print(repr(resp))


    # Check if the experience layer said they gave us incorrect information
    if not resp or not resp.json()['ok']:
      # Couldn't log them in, send them back to login page with error
        return render(request, 'login.html', {'form': form, 'text': text})

    """ If we made it here, we can log them in. """
    # Set their login cookie and redirect to back to wherever they came from
    resp = resp.json()
    authenticator = resp['resp']['authenticator']
    response = HttpResponseRedirect(nextpage)
    response.set_cookie("auth", authenticator)

    return response

def logout(request):
    if 'auth' in request.COOKIES:
        resp = requests.post('http://exp-api:8000/v1/api/logout/', request.COOKIES)
    return HttpResponseRedirect('/')