Contribution Guidelines
=======================

This document describes how to contribute code and other content to the
Gnawts project.

How To Contribute
-----------------

* Clone: `git clone git://github.com/hpc/gnawts.git`
* Create a topic branch: `git checkout -b awesome_feature`
* Commit away.
* Keep up to date: `git fetch && git rebase origin/master`.

Once you’re ready:

* Fork the project on GitHub
* Add your repository as a remote: `git remote add your_remote your_repo`
* Push up your branch: `git push your_remote awesome_feature`
* Create a Pull Request for the topic branch, asking for review.

Branching
---------

For your own development, use the topic branches. Basically, cut each
feature into its own branch and send pull requests based off those.

On the main repo, branches are used as follows:

<table>
    <thead>
        <tr>
            <th>Branch</th>
            <th>Used for...</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>`master`</td>
            <td>The main development branch. **Always** should be fast-forwardable.</td>
        </tr>
    </tbody>
</table>
