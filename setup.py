from setuptools import setup, find_packages
from codecs import open
import os
from gcdt import __version__

here = os.path.abspath(os.path.dirname(__file__))
if not os.getenv('ghprbPullId', None):
    version = __version__
else:
    version = 'PR%s' % os.getenv('ghprbPullId')

# Get the long description from the README file
try:
    import pypandoc
    long_description = pypandoc.convert('README.md', format='md', to='rst')
except(IOError, ImportError):
    with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
        long_description = f.read()

# get the dependencies and installs
with open(os.path.join(here, 'requirements.txt'), encoding='utf-8') as f:
    all_reqs = f.read().split('\n')


install_requires = [x.strip() for x in all_reqs if ('git+' not in x) and
                    (not x.startswith('#')) and (not x.startswith('-'))]
dependency_links = [x.strip().replace('git+', '') for x in all_reqs if 'git+' not in x]

setup(
    name='gcdt',
    version=version,
    description='Glomex Cloud Deployment Tools',
    long_description=long_description,
    url='https://github.com/glomex/gcdt',
    #download_url='http://invalidurl.invalid/gcdt/tarball/' + version,
    license='MIT',
    classifiers=[
        'Natural Language :: English',
        'Intended Audience :: Developers',
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='',
    packages=find_packages(exclude=['docs', 'tests*']),
    include_package_data=True,
    author='Glomex DevOps Team',
    install_requires=install_requires,
    dependency_links=dependency_links,
    author_email='Mark.Fink@glomex.com',
    entry_points={
        'console_scripts': [
            'gcdt=gcdt.gcdt_main:main',
            'kumo=gcdt.kumo_main:main',
            'ramuda=gcdt.ramuda_main:main',
            'yugen=gcdt.yugen_main:main',
            'tenkai=gcdt.tenkai_main:main'
        ]
    }
)
