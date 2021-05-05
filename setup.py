import setuptools

setuptools.setup(
    name='HawkEye',
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    author='',
    author_email='',
    url='https://github.com/Toolage13/HawkEye',
    packages=setuptools.find_packages(),
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    install_requires=[
        'wxPython>=4.1.1',
        'requests>=2.25.1',
    ],
    python_requires='>=3.6, <4',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    entry_points={
        'console_scripts': [
            'hawkeye = hawkeye.__main__.main'
        ]
    }
)