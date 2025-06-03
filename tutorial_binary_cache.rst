.. Copyright 2013-2023 Lawrence Livermore National Security, LLC and other
   Spack Project Developers. See the top-level COPYRIGHT file for details.

   SPDX-License-Identifier: (Apache-2.0 OR MIT)

.. include:: common/setup.rst

.. _binary-cache-tutorial:

==================================
Binary Caches Tutorial
==================================

Tired of waiting for software to compile? Wish you could share your exact software environment with teammates effortlessly? Binary caches are here to help! They save you valuable time by storing pre-compiled software packages, ensure everyone on your team uses the exact same versions, and make sharing complex setups a breeze.

This tutorial will guide you through the world of Spack binary caches. You'll learn:

*   What binary caches are and why they're awesome.
*   How to set up your own binary cache, with a special focus on using OCI container registries (like Docker Hub or GitHub Packages).
*   How to push packages to your cache and pull them on different machines or for other users.
*   How to even create runnable container images directly from your cached packages!

Imagine you're working on a project with a team. Everyone needs the same complex software, but compiling it on each machine is time-consuming and error-prone. Binary caches solve this! You compile it once, store it in a cache, and everyone else can grab the ready-to-use version in minutes.

Let's dive in and learn how to make your software management smoother and faster!

Before we configure a build cache, let's install the ``julia`` package. We choose ``julia`` because it has some non-trivial dependencies (like ``llvm``) and features an interactive Read-Eval-Print Loop (REPL). This makes it a good candidate to demonstrate the utility of binary caches and allows us to easily verify that our installations are working.

First, let's set up a directory for our work and create a Spack environment. Spack environments provide isolated spaces for package installations, ensuring that this tutorial won't interfere with your other Spack setups. The ``--with-view view .`` option creates a directory named `view` containing symlinks to the installed executables, making them easily accessible.

.. code-block:: console

   $ mkdir ~/myenv && cd ~/myenv
   $ spack env create --with-view view .

Next, within this environment, we'll specify that we want to install ``julia`` and then proceed with the installation. Spack will download ``julia`` and all its dependencies, compile them from source, and install them into the environment.

.. code-block:: console

   $ spack -e . add julia
   $ spack -e . install

To confirm that ``julia`` was installed correctly and is usable, let's run its REPL from the view directory and perform a simple calculation.

.. code-block:: console

   $ ./view/bin/julia
   julia> 1 + 1
   2

Now we'd like to share these executables with other users.
First we will focus on sharing the binaries with other *Spack* users, and later we will see how users completely unfamiliar with Spack can easily use the applications too. To do this, we first need to set up a binary cache where these compiled packages can be stored.

------------------------------------------------
Setting up an OCI build cache on GitHub Packages
------------------------------------------------

For this tutorial we will be using GitHub Packages as an OCI registry, since most people have a GitHub account and it's easy to use. An OCI (Open Container Initiative) registry is typically used for storing Docker images, but Spack can also use it to store binary packages.

First, you'll need a GitHub Personal Access Token (PAT). This token acts like a password for Spack to authenticate with GitHub Packages.
Navigate to `<https://github.com/settings/tokens>`_ in your browser. Click on "Generate new token" and select "Generate new token (classic)".
You must grant this token the ``write:packages`` scope; this permission allows Spack to upload (write) packages to your GitHub Packages registry. Add a note for the token's purpose (e.g., "Spack tutorial cache") and click the "Generate token" button at the bottom of the page.
**Important:** After the token is generated, copy it immediately to a secure location. GitHub will not show it to you again.

With your PAT copied, the next step is to configure Spack to use GitHub Packages as a binary cache.
As a security best practice, avoid pasting your PAT directly into commands or configuration files. Instead, store it in an environment variable. In your terminal, replace `<paste-your-token-here>` with the actual token you just generated:

.. code-block:: console

   $ export MY_OCI_TOKEN=<paste-your-token-here>

Now, you'll instruct Spack to use this PAT and your GitHub Packages account as a binary cache. This is done using the `spack mirror add` command, which registers a new remote location (your cache) with the current Spack environment.

Let's break down the command you're about to run:
*   Replace `<your-github-username>` with your actual GitHub username. This is the username associated with your PAT.
*   Replace `<your-github-username-or-org>` with your GitHub username or the name of a GitHub organization where you have the necessary permissions to create packages. This determines where the cache will be hosted on GitHub.
*   The OCI URL, `oci://ghcr.io/<your-github-username-or-org>/buildcache-${USER}-${HOSTNAME}`, defines the remote location and name of your cache.
    *   `oci://` specifies the protocol for an OCI registry.
    *   `ghcr.io` is the hostname for GitHub's Container Registry.
    *   The part after `ghcr.io/` (i.e., `<your-github-username-or-org>/buildcache-${USER}-${HOSTNAME}`) becomes the unique name of your package repository within GitHub Packages. The `${USER}-${HOSTNAME}` part uses shell environment variables for your current username and machine hostname to suggest a unique name for the cache itself; you can customize this if you wish (e.g., `my-spack-cache`).

Execute the following command, substituting your details:

.. code-block:: console

   $ spack -e . mirror add \
       --oci-username <your-github-username> \
       --oci-password-variable MY_OCI_TOKEN \
       --unsigned \
       my-mirror \
       oci://ghcr.io/<your-github-username-or-org>/buildcache-${USER}-${HOSTNAME}

Here's what each option does:
*   `--oci-username <your-github-username>`: Provides your GitHub username for authenticating to the OCI registry.
*   `--oci-password-variable MY_OCI_TOKEN`: Instructs Spack to read the PAT from the `MY_OCI_TOKEN` environment variable you set earlier.
*   `--unsigned`: For simplicity in this tutorial, we are not cryptographically signing the packages. In a production or security-conscious environment, you would likely omit this or use `--signed` and configure signing keys.
*   `my-mirror`: This is a friendly, local name that Spack will use in this environment to refer to this specific build cache. You'll use this name in other Spack commands.
*   The final argument is the full OCI URL that uniquely identifies your build cache's location in GitHub Packages.

.. note ::

We talk about mirrors and build caches almost interchangeably, because every build cache is a binary mirror (it mirrors binaries).
Source mirrors also exist (mirroring source code), which we will not cover in this tutorial.

After successfully executing `spack mirror add`, Spack records this configuration in your environment's ``spack.yaml`` file. This file holds all the specific settings for the current Spack environment. You should see a new `mirrors:` section that looks similar to this (the exact URL will reflect your inputs):

.. code-block:: yaml

   spack:
     specs:
     - julia
     mirrors:
        my-mirror:
           url: oci://ghcr.io/<github_user>/buildcache-<user>-<host>
           access_pair:
              id: <user>
              secret_variable: MY_OCI_TOKEN
           signed: false

Let's re-examine this YAML snippet to understand how Spack stored the configuration:
*   `spack:`: The main key for all Spack environment settings.
*   `specs:`: This lists the packages you've explicitly added to the environment (like `julia`).
*   `mirrors:`: This section contains definitions for one or more binary caches.
    *   `my-mirror:`: This is the configuration block for the cache we named `my-mirror`.
        *   `url:`: The full OCI URL you provided, pointing to your cache on GitHub Packages. Spack might show placeholders here like `<github_user>` if it can infer parts of the URL from context, but it resolves to the full URL you specified.
        *   `access_pair:`: This sub-section holds the authentication details.
            *   `id:` Your GitHub username (matching `--oci-username`).
            *   `secret_variable:` The name of the environment variable (`MY_OCI_TOKEN`) that Spack will use to find your PAT (matching `--oci-password-variable`).
        *   `signed: false`: Reflects that this cache does not require signed packages (matching `--unsigned`).

With the mirror successfully configured in ``spack.yaml``, your Spack environment now knows about your personal OCI build cache. The next logical step is to populate this cache with the software you've built.
To do this, use the `spack buildcache push` command. This command will take the `julia` package (and its dependencies) that you installed locally earlier and upload them to `my-mirror`.

.. code-block:: console

   $ spack -e . buildcache push my-mirror

You should see output similar to the following, indicating the progress:

.. code-block:: text

   ==> Selected 66 specs to push to oci://ghcr.io/<github_user>/buildcache-<user>-<host>
   ==> Checking for existing specs in the buildcache
   ==> 66 specs need to be pushed to ghcr.io/<github_user>/buildcache-<user>-<host>
   ==> Uploaded sha256:d8d9a5f1fa443e27deea66e0994c7c53e2a4a618372b01a43499008ff6b5badb (0.83s, 0.11 MB/s)
   ...
   ==> Uploading manifests
   ==> Uploaded sha256:cdd443ede8f2ae2a8025f5c46a4da85c4ff003b82e68cbfc4536492fc01de053 (0.64s, 0.02 MB/s)
   ...
   ==> Pushed zstd@1.5.6/ew3aaos to ghcr.io/<user>/buildcache-<user>-<host>:zstd-1.5.6-ew3aaosbmf3ts2ylqgi4c6enfmf3m5dr.spack
   ...
   ==> Pushed julia@1.9.3/dfzhutf to ghcr.io/<user>/buildcache-<user>-<host>:julia-1.9.3-dfzhutfh3s2ekaltdmujjn575eip5uhl.spack

Here's what the key parts of the output mean:
*   `==> Selected 66 specs to push...`: Spack has identified 66 packages (julia and its dependencies) that are eligible to be pushed.
*   `==> Checking for existing specs in the buildcache`: It first checks if any of these are already present in your `my-mirror` cache.
*   `==> 66 specs need to be pushed...`: In this case, none were present, so all 66 will be uploaded.
*   `==> Uploaded sha256:d8d9a5f...`: This shows individual binary tarballs (and their checksums) being uploaded to the OCI registry.
*   `==> Uploading manifests`: After the package data, Spack uploads metadata (manifests) for these packages.
*   `==> Pushed zstd@1.5.6/ew3aaos to ...`: Finally, it confirms each package (like `zstd` and `julia` themselves) that has been successfully pushed to your OCI build cache. The long string after the package name (e.g., `ew3aaos...`) is the Spack hash identifying this specific build.

The location of the pushed package, when referred to as an OCI image (which we'll explore later), will be something like:

.. code-block:: text

   ghcr.io/<github_user>/buildcache-<user>-<host>:julia-1.9.3-dfzhutfh3s2ekaltdmujjn575eip5uhl.spack

This looks very similar to a Docker container image tag. The `.spack` suffix is a convention Spack uses for these OCI artifacts to distinguish them from regular container images, though they are stored using the same underlying technology. We will get to that in a bit.

.. note ::

By default, packages pushed to GitHub Packages are ``private``. This means only you (or those with whom you've shared the PAT or granted access via GitHub permissions) can download them.
If you want others to be able to use your build cache without a token, you can change the package visibility to ``public``.
To do this, go to your GitHub Packages page (usually `https://github.com/<your-github-username>?tab=packages`), select the ``buildcache-...`` package you just created, go to ``package settings``, and change the visibility to ``public`` in the ``Danger Zone`` section.
This page can also be directly accessed by going to:

   .. code-block:: text

      https://github.com/users/<user>/packages/container/buildcache/settings

With your packages pushed, the cache is ready to be used.
-------------------------------
Installing from the build cache
-------------------------------

We will now verify that the build cache works by reinstalling ``julia`` from it.

To ensure Spack *only* uses the build cache we just created for this specific test (and not any other globally configured Spack mirrors, like the default Spack public binary cache, or any mirrors defined in your `~/.spack/config.yaml`), we will temporarily override the ``mirrors`` configuration for the current environment.
We do this by modifying the ``spack.yaml`` file. The key is the double colon syntax: ``mirrors::``.
In Spack's configuration system:
*   A single colon (e.g., `mirrors:`) appends to or merges with existing configurations at higher scopes (like user or site configurations).
*   A double colon (e.g., `mirrors::`) **completely replaces** any configuration for that item from higher scopes.
So, using `mirrors::` tells Spack: "For this environment, ignore all other mirror definitions and use *only* the ones listed below." This is crucial for verifying that our specific cache `my-mirror` is being used.

Your ``spack.yaml`` should be modified to look like this:

.. code-block:: yaml

   spack:
     specs:
     - julia
     mirrors::  # <- note the double colon, this is important!
        my-mirror:
           url: oci://ghcr.io/<github_user>/buildcache-<user>-<host> # Same URL as before
           access_pair:
              id: <user> # Your GitHub username
              secret_variable: MY_OCI_TOKEN # The env var holding your PAT
           signed: false # Still using unsigned packages

With this configuration, Spack has no choice but to try and fetch `julia` (and its dependencies) from `my-mirror` if they are needed for an installation.

Now, let's force Spack to reinstall ``julia``. We use the ``--overwrite`` flag because ``julia`` is already installed in our environment. This flag tells Spack to proceed with the installation logic even for already-installed packages, which in this case, means it will have to consult available mirrors – and thanks to our `mirrors::` setting, `my-mirror` is the only one it will consider. This is how we test if our cache is being correctly utilized.

.. code-block:: console

   $ spack -e . install --overwrite julia

If the build cache is working correctly, you should see output indicating that Spack is fetching and installing ``julia`` from your cache. The output will vary based on your specific username and cache name, but look for lines like these:

.. code-block:: text

   ==> Fetching https://ghcr.io/v2/<user>/buildcache-<user>-<host>/blobs/sha256:34f4aa98d0a2c370c30fbea169a92dd36978fc124ef76b0a6575d190330fda51
   ==> Fetching https://ghcr.io/v2/<user>/buildcache-<user>-<host>/blobs/sha256:3c6809073fcea76083838f603509f10bd006c4d20f49f9644c66e3e9e730da7a
   ==> Extracting julia-1.9.3-dfzhutfh3s2ekaltdmujjn575eip5uhl from binary cache
   [+] /home/spack/spack/opt/spack/linux-ubuntu22.04-x86_64_v3/gcc-11.4.0/julia-1.9.3-dfzhutfh3s2ekaltdmujjn575eip5uhl

Key things to note in this output, confirming your cache is working:
*   The `Fetching https://ghcr.io/...` lines are the most direct evidence. They show Spack downloading files (called "blobs" in OCI terminology) directly from your GitHub Container Registry URL (where `<user>/buildcache-<user>-<host>` matches your cache name).
*   The line `==> Extracting julia-... from binary cache` explicitly confirms that the `julia` package itself is being sourced from a pre-compiled binary cache, not built from source.
*   The `[+] /home/spack/spack/opt/spack/...` line shows the final installation path of `julia`, successfully installed from the cached binary.

Spack typically fetches two "blobs" for each package from an OCI cache: one contains metadata about the package (the manifest, detailing its hash, dependencies, compiler, etc.), and the other is the compressed tarball of the actual compiled binaries and files.
If you've used ``docker pull`` or other container runtimes before, these types of content-addressed ``sha256:...`` hashes may look familiar.
OCI registries are content addressed, which means that we see hashes like these instead of human-readable file names.
Successfully installing from your own cache is a great first step. Now, let's explore how Spack optimizes the use of these caches, especially for other users or different environments.

------------------------------------
Reuse of binaries from a build cache
------------------------------------

Spack's true power shines when its **concretizer** (the component that resolves all dependencies, versions, and build options for a package) can intelligently **reuse** binaries from a build cache. This means that when you ask Spack to install a package, it will try to find compatible, pre-built binaries in its known caches to satisfy dependencies, rather than building everything from source each time. This dramatically speeds up software deployment.

In the previous example, we forced an installation from our cache. But for Spack's concretizer to automatically consider your `my-mirror` cache during its decision-making process for *future* installations or when resolving dependencies for new packages, it needs to know what packages are available in that cache. This is where indexing comes in.

The command ``spack buildcache update-index my-mirror`` connects to your `my-mirror` cache and downloads metadata for all the packages it contains. This metadata is stored locally as an index. When the concretizer runs, it consults this local index. If it finds a binary in `my-mirror` that matches a required dependency (considering version, compiler, architecture, etc.), it will prefer using that binary over a source build. Without an up-to-date index, the concretizer is essentially unaware of your cache's contents.

.. code-block:: console

   $ spack -e . buildcache update-index my-mirror

This indexing operation can take a while for very large build caches, as it needs to fetch metadata for all available packages.
For convenience, if you are pushing packages and want to immediately update the index, you can run ``spack buildcache push --update-index my-mirror``.


.. note::

   As of Spack 0.22, build caches can be used across different Linux distros.
   The concretizer will reuse specs that have a host-compatible ``libc`` dependency (e.g. ``glibc`` or ``musl``).
   For packages compiled with ``gcc`` (and a few other compilers), users do not have to install compilers first, as the build cache contains the compiler runtime libraries as a separate package dependency. This greatly enhances binary portability.

After an index is created for your mirror, you can use ``spack buildcache list`` to see the packages that Spack (via its local index) knows are available in that specific cache.
Using ``--allarch`` shows packages compatible with any architecture, not just your current machine's. The output will list all packages you've pushed to `my-mirror` and indexed, such as `julia` and its dependencies. This helps you verify what the concretizer can "see" in your cache.

.. code-block:: console

   $ spack -e . buildcache list --allarch

Beyond sharing Spack packages among Spack users, OCI-based build caches offer another powerful capability: creating runnable container images directly.

----------------------------------
Creating runnable container images
----------------------------------

The build cache we have created uses an OCI registry, which is the same technology that is used to store container images.
So far we have used this build cache as any other build cache: the concretizer can use it to avoid source builds, and ``spack install`` will fetch binaries from it.

However, we can also use this build cache to share binaries directly as runnable container images. This is a powerful feature of using an OCI registry as the backend for your Spack build cache.

Let's see what happens if we try to run the OCI image for `julia` (that Spack pushed earlier) directly using Docker. Remember, this initial OCI artifact created by Spack contains just the `julia` package and its Spack-managed dependencies, not a complete operating system.
You'll need to use the OCI image location that was displayed after your `spack buildcache push` command. It will look something like `ghcr.io/<user>/buildcache-<user>-<host>:julia-1.9.3-dfzhutfh3s2ekaltdmujjn575eip5uhl.spack`.
The command `docker run <image_name> julia` attempts to start a container from the specified image and execute the `julia` command within it.

.. code-block:: console

   $ docker run ghcr.io/<user>/buildcache-<user>-<host>:julia-1.9.3-dfzhutfh3s2ekaltdmujjn575eip5uhl.spack julia
   exec /home/spack/spack/opt/spack/linux-ubuntu22.04-x86_64_v3/gcc-11.4.0/julia-1.9.3-dfzhutfh3s2ekaltdmujjn575eip5uhl/bin/julia: no such file or directory

But it immediately fails! The error `no such file or directory`, while slightly misleading in this container context, typically means that the `julia` executable itself was found (it's in the image), but an essential system library it dynamically links against at runtime is missing from this very minimal image. The most common missing piece is the C standard library (e.g., `glibc`), which applications expect the operating system to provide. Spack generally treats `glibc` as an external, OS-provided package, so it's not bundled *inside* the `julia` package's OCI artifact. The raw Spack OCI artifact is therefore not a bootable OS, just the software itself.

To make this runnable, we need to combine Spack's `julia` package with an actual OS environment. Spack allows us to do this by layering its package on top of an existing base container image (like `ubuntu:24.04`) when pushing to the cache. This base image provides the foundational OS layers, including `glibc`, a shell, and other utilities.
OCI images are built in layers; the base image forms the initial layers, and Spack will add the `julia` package as new layers on top.

Let's re-push our `julia` package. This time, we'll use the ``--base-image ubuntu:24.04`` option. This tells Spack to use the official `ubuntu:24.04` image as the starting point and then add `julia` to it. We also need the ``--force`` flag. This is because an image tag `julia-1.9.3-...spack` already exists in your cache (from the previous push). The ``--force`` flag allows Spack to overwrite this existing tag with the new, layered image.

.. code-block:: console

   $ spack -e . buildcache push --force --base-image ubuntu:24.04 my-mirror
   ...
   ==> Pushed julia@1.9.3/dfzhutf to ghcr.io/<user>/buildcache:julia-1.9.3-dfzhutfh3s2ekaltdmujjn575eip5uhl.spack

The output confirms that `julia` (and its dependencies, if they also needed updating) are pushed again, now incorporating the base image.

With the image repushed including a base layer, let's try pulling and running it again.
First, `docker pull` ensures you have the latest version of the image (the one with the base layer).
Then, `docker run -it --rm ...` runs the container:
*   `-it` gives you an interactive terminal connected to the container.
*   `--rm` tells Docker to automatically remove the container when you exit it.
This time, we just run the image itself, and then execute `julia` from within the container's shell.

.. code-block:: console

   $ docker pull ghcr.io/<github_user>/buildcache-<user>-<host>:julia-1.9.3-dfzhutfh3s2ekaltdmujjn575eip5uhl.spack
   $ docker run -it --rm ghcr.io/<github_user>/buildcache-<user>-<host>:julia-1.9.3-dfzhutfh3s2ekaltdmujjn575eip5uhl.spack
   root@f53920f8695a:/# julia
   julia> 1 + 1
   2

This time it works!
The `root@f53920f8695a:/#` prompt shows you are inside the running container. Typing `julia` starts the REPL, and `1 + 1` correctly yields `2`.
The minimal ``ubuntu:24.04`` base image provides not only the necessary ``glibc`` but also other utilities like a shell, making the environment runnable and interactive.

Notice that you can use any base image of choice, such as ``fedora`` or ``rockylinux``, as long as it's compatible.
The only critical constraint is that the base image must have a ``libc`` (like glibc or musl) that is binary compatible with the ``libc`` Spack used when it originally built the binaries for ``julia``. Spack does not currently validate this compatibility, so choosing an appropriate base image is important.
This demonstrates how to package a single application. But what if you want to package a full environment with multiple tools?

--------------------------------------
Spack environments as container images
--------------------------------------

The previous container image for a single package is a good start, but it would be nice to add some more utilities to the image, effectively packaging a whole environment.
Spack's OCI build cache capabilities extend to this as well. When you push packages to an OCI registry, Spack not only creates an image layer (and potentially a tag) for each individual package but can also create a tag for an entire Spack environment.

If you've paid attention to the output of some of the commands we have run so far, you may have noticed that Spack generates exactly one image tag for each package it pushes to the registry (e.g., `julia-1.9.3-dfzhutfh3s2ekaltdmujjn575eip5uhl.spack`). Each Spack package effectively becomes a layer in the OCI image. These layers are shared across different image tags if the underlying package is the same.

Because Spack installs every package into a unique prefix, it is incredibly easy to compose multiple packages into a single, coherent container image. This is different from traditional `Dockerfile` approaches where commands run in sequence; Spack package layers are more independent and composable.

Let's enhance our environment by adding a simple text editor, ``vim``, alongside ``julia``. This will allow us to both edit and run Julia code within the same container.
The command ``spack -e . install --add vim`` first adds `vim` to your environment's `spack.yaml` `specs` list and then installs `vim` and its dependencies.

.. note::

   Remember our ``mirrors::`` setting in ``spack.yaml``? If it's still in place, Spack will only look at `my-mirror`. If `vim` isn't in `my-mirror` (which it likely isn't yet), Spack will try to build `vim` from source. This should be relatively quick.
   If you wanted Spack to check other mirrors (like the main Spack binary cache, which might have `vim`) before building, you would change ``mirrors::`` back to ``mirrors:`` in your ``spack.yaml``. For this exercise, building `vim` is fine.

.. code-block:: console

   $ spack -e . install --add vim

Now, when we push the contents of our environment to the OCI registry, we'll use the ``--tag julia-and-vim`` option. This tells Spack to create an additional, human-readable OCI image tag named `julia-and-vim`. This tag will reference an image that includes all packages currently in your Spack environment (i.e., `julia`, `vim`, and all their dependencies), layered on top of the specified base image.

.. code-block:: console

   $ spack -e . buildcache push --base-image ubuntu:24.04 --tag julia-and-vim my-mirror
   ==> Tagged ghcr.io/<user>/buildcache:julia-and-vim

The output `==> Tagged ghcr.io/<user>/buildcache:julia-and-vim` confirms that this new environment-wide tag has been created in your OCI registry. (The `<user>/buildcache` part will correspond to your specific OCI namespace and cache name).

Now, let's run a container from this comprehensive environment image. We use the new `julia-and-vim` tag:

.. code-block:: console

   $ docker run -it --rm ghcr.io/<github_user>/buildcache-<user>-<host>:julia-and-vim
   root@f53920f8695a:/# vim ~/example.jl  # create a new file with some Julia code
   root@f53920f8695a:/# julia ~/example.jl  # and run it

Inside the container, you can now use `vim` to create a Julia script (e.g., `~/example.jl` containing `println("Hello from Julia in Spack container!")`) and then execute it with `julia ~/example.jl`. This demonstrates that both tools are available and functional within the single container image, showcasing the power of packaging entire Spack environments.

You've now seen how Spack can directly create OCI images. This might lead you to wonder how this compares to traditional Dockerfile-based approaches.
------------------------------------
Do I need ``docker`` or ``buildah``?
------------------------------------

In older versions of Spack, a common way to create container images was to first use the ``spack containerize`` command. This command generates a ``Dockerfile``. You would then use ``docker build`` (or a similar tool like ``buildah``) with this ``Dockerfile`` to produce a container image.

This ``Dockerfile`` typically defined a multi-stage build:
1.  **Build Stage:** The first stage would start from a base image, install Spack itself, copy your environment configuration (e.g., `spack.yaml`), and then run `spack install` to build all the packages in your environment.
2.  **Final Stage:** The second stage would start from a clean (often identical) base image and then copy only the installed package tree from the build stage (e.g., from `/opt/spack/opt` in the build stage) into the final image. This results in a smaller final image that doesn't contain Spack itself or any intermediate build tools.

For those familiar with ``Dockerfile`` syntax, it would structurally look something like this:

.. code-block:: Dockerfile

   # Stage 1: Build Spack and the environment
   FROM <base image> AS build
   # Commands to install Spack itself would go here
   # ...
   # Copy the environment definition
   COPY spack.yaml /root/env/spack.yaml
   # Run Spack to install all packages in the environment
   RUN spack -e /root/env install

   # Stage 2: Create the final, smaller image
   FROM <base image>
   # Copy only the installed packages from the build stage
   COPY --from=build /opt/spack/opt /opt/spack/opt

This ``spack containerize`` approach is still available and valid, but directly using ``spack buildcache push`` (as shown in this tutorial) to create OCI images has some advantages and avoids a few downsides of the Dockerfile method:

*   **Build Failures and Caching:** If the `RUN spack -e /root/env install` command fails during a `docker build`, Docker typically doesn't cache the partially successful layer. This means if one package in a long list fails to build, you lose the successful builds of all preceding packages in that layer, and troubleshooting often means restarting the entire (potentially lengthy) build. With `spack install` run directly on the host or in a more controlled environment, Spack's own build cache can save progress.
*   **Docker-in-Docker Complexity:** In certain Continuous Integration (CI) environments, the CI script itself might already be running inside a Docker container. Running `docker build` from within another Docker container (often called "Docker-in-Docker" or DinD) can be complex to set up safely and securely.

The key takeaway is that Spack's direct OCI integration (via ``spack buildcache push``) effectively decouples the steps that ``docker build`` usually combines:
1.  **Build Isolation & Execution:** You can run ``spack install`` on your host machine, in a dedicated build container, or wherever is most convenient, leveraging Spack's build cache for efficiency.
2.  **Image Creation:** You then run ``spack buildcache push`` separately to package these already-built binaries into an OCI image.

This separation provides more flexibility and can simplify the build and image creation pipeline.
Whether you're creating images directly with Spack or using other methods, a crucial concept when sharing binaries is relocation.

----------
Relocation
----------

Spack is different from many package managers in that it allows users to choose almost any location to install packages. This provides great flexibility, as users don't need root privileges and can manage their own software installations in their home directories or project spaces.

However, this flexibility presents a challenge when sharing pre-compiled binaries. During compilation, software often embeds absolute paths to its dependencies or its own data files directly into the executable files or libraries. If you then move these binaries to a new machine or a different path (which is exactly what happens when installing from a binary cache), these hard-coded paths will point to non-existent locations, and the software will likely fail to run. This is known as the "relocation problem."

Fortunately, Spack has built-in mechanisms to attempt to fix these embedded paths when it installs a package from a binary cache. It scans the binary files for known installation paths and tries to rewrite them to the new target location.

However, there's a critical detail: Spack can generally only make these embedded paths *shorter*.
The reason is that these paths are often stored as strings in fixed-size areas within the binary files (like string tables). If a new path is longer than the original path that was embedded during compilation, writing the new path would overwrite adjacent data, corrupting the binary. But if the new path is shorter, Spack can replace the longer path with the shorter one and pad the rest with null characters, which is usually safe.

So, to maximize the chances that your binaries can be successfully relocated and used by others, you should build them in a Spack instance where the installation paths (prefixes) are *longer* than the paths where they are likely to be installed from the cache.
Spack provides a convenient way to achieve this using path padding. By setting the `config:install_tree:padded_length` configuration, you instruct Spack to artificially extend its installation paths with extra characters (padding) up to a specified length during the initial build.

For example, to make all installation prefixes 256 characters long, you would add the following configuration to your environment (or your global `config.yaml`):

.. code-block:: console

   $ spack -e . config add config:install_tree:padded_length:256

When Spack builds software with this setting, the embedded paths will be long (e.g., `/path/to/spack/opt/very/long/padding/....................../package-version`). Later, when someone installs this package from your binary cache into a typical, shorter path (e.g., `/home/user/spack/opt/package-version`), Spack can safely rewrite the long, padded path to the shorter actual path.
This significantly improves the relocatability and reusability of your cached binaries.

Ensuring your binaries are relocatable is key for sharing. One of the most impactful places to leverage shared binaries is in Continuous Integration (CI) pipelines.
------------------------
Using build caches in CI
------------------------

Build caches are a great way to speed up Continuous Integration (CI) pipelines. Instead of recompiling all your project's dependencies from scratch in every CI run, you can pull them from a build cache.
Both major CI platforms, GitHub Actions and GitLab CI, have excellent support for using container registries, which, as you've seen, can host Spack build caches. The principles discussed in this tutorial for setting up and using an OCI-based build cache apply directly to CI environments.

Spack also provides a dedicated GitHub Action, ``spack/setup-spack``, which simplifies the process of using Spack within GitHub Actions. This action not only installs Spack but can also configure it to use a public binary cache (often the one at `cache.spack.io`) by default.

Here's a very basic example of how you might use it in a GitHub Actions workflow file (e.g., `.github/workflows/main.yaml`):

.. code-block:: yaml

   jobs:
     build:
       runs-on: ubuntu-22.04  # Specifies the CI runner environment
       steps:
       - name: Set up Spack   # A descriptive name for this step
         uses: spack/setup-spack@v2  # Invokes the official Spack setup action
         # This action installs Spack and by default configures a shared binary cache.

       - name: Install Python using Spack
         run: spack install python  # Spack attempts to install python
         # If a compatible python is in the configured cache, it's downloaded.
         # Otherwise, Spack builds it (and could push to your own cache if configured).

In this workflow:
*   `jobs: build: runs-on: ubuntu-22.04`: Defines a job named `build` that will execute on a fresh Ubuntu 22.04 virtual machine provided by GitHub.
*   `steps: - name: Set up Spack / uses: spack/setup-spack@v2`: This is the core Spack setup. The `spack/setup-spack` action handles downloading Spack, adding it to the PATH, and basic configuration, often including a pre-configured public binary cache.
*   `- run: spack install python`: This command then uses the initialized Spack instance to install Python. Because `setup-spack` often configures a shared cache, there's a good chance a common package like `python` will be fetched as a pre-built binary, significantly speeding up this step in your CI pipeline.

The `setup-spack readme <https://github.com/spack/setup-spack>`_ provides much more detail on how to configure it, including how to set up your own private build caches for use in CI, so your CI can benefit from caching your project's specific dependencies.
As you can see, binary caches are a versatile tool for both individual developers and automated systems, streamlining software deployment and reducing build times.

-------
Summary
-------

In this tutorial, we have created a build cache on top of an OCI registry, which can be used:

* to run ``spack install julia vim`` on machines and have Spack fetch pre-built binaries instead of building from source.
* to automatically create container images for individual packages when pushing to the cache.
* to create container images for entire Spack environments (multiple packages) at once.
