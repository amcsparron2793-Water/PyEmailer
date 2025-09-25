from setuptools import setup
import re

project_name = 'PyEmailerAJM'


def get_property(prop, project):
    result = re.search(r'{}\s*=\s*[\'"]([^\'"]*)[\'"]'.format(prop),
                       open(project + '/_version.py').read())
    return result.group(1)


setup(
    name=project_name,
    version=get_property('__version__', project_name),
    packages=['PyEmailerAJM', 'PyEmailerAJM.backend',
              'PyEmailerAJM.continuous_monitor', 'PyEmailerAJM.msg',
              'PyEmailerAJM.searchers'],
    url='https://github.com/amcsparron2793-Water/PyEmailer',
    download_url=f'https://github.com/amcsparron2793-Water/PyEmailer/archive/refs/tags/{get_property("__version__", project_name)}.tar.gz',
    keywords=["Outlook", "Email", "Automation"],
    install_requires=['pywin32', 'extract_msg', 'email_validator', 'questionary', 'EasyLoggerAJM', 'ColorizerAJM'],
    license='MIT License',
    author='Amcsparron',
    author_email='amcsparron@albanyny.gov',
    description='Allows for automating sending Email with the Outlook Desktop client.'
                ' Future releases will add more client support'
)
