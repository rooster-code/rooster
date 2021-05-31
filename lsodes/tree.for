lsodes:

! BLOCK A. executed on every call. it tests istate and itask for legality and branches appropriately.
  ...

  ! for the initial call (istate = 1), or for a continuation call with parameter changes (istate = 3) 
  if(istate .eq. 1 .or. istate .eq. 3)then
     ...
     ! BLOCK B. for checking of all inputs and various initializations. 
     ...

     ! for the initial call only (istate = 1)
     if(istate .eq. 1)then

        ! BLOCK C. all remaining initializations, the initial call to f, the sparse matrix preprocessing, and the calculation of the initial step size. 
        ...
        ! initial call to f.
        call rhs(neq, t, y, rwork(lf0))
        ...
        ! load and invert the error weights in ewt.  (h is temporarily set to 1.0.)
        call ewset(n, itol, rtol, atol, rwork(lyh), rwork(lewt))
        ...

        ! miter indicates the corrector iteration method
        if(miter .eq. 1 .or. miter .eq. 2)then
           ! sparse matrix preprocessing
           call iprep(neq, y, rwork, iwork(lia), iwork(lja), ipflag)
                └─ ...
                   call prep(neq, y, rwork(lyh), rwork(lsavf), rwork(lewt), rwork(lacor), ia, ja, rwork(lwm), rwork(lwm), ipflag)
                        └─ ...
                           ! moss indicates the method to be used to obtain the sparsity structure of the jacobian matrix
                           
                           ! moss = 1 : user has supplied fjac and the structure will be obtained from neq initial calls to fjac
                           if(moss .eq. 1)then
                              ! a dummy call to rhs allows user to create temporaries for use in fjac.
                              call rhs(neq, tn, y, savf)
                              ...
                              do j = 1,n
                                 ...
                                 call fjac(neq, tn, y, j, iwk(ipian), iwk(ipjan), savf)
                                 ...
                              end do
                           end if

                           if(moss .eq. 2)then
                              ! moss = 2. compute jacobian structure from results of n + 1 calls to rhs
                               ...
                               call rhs(neq, tn, y, savf)
                               do j = 1,n
                                  ...
                                  call rhs(neq, tn, y, ftem)
                                  ...
                               end do
                           end if

                           ! miter = 2 : chord iteration with an internally generated (difference quotient) sparse jacobian
                           if(miter .eq. 2)then
                              ! compute grouping of column indices.
                              ...
                              call jgroup (n, iwk(ipian), iwk(ipjan), maxg, ngp, iwk(ipigp), iwk(ipjgp), iwk(iptt1), iwk(iptt2), ier)
                              ...
                           end if
                           ...
                           ! compute new ordering of rows/columns of jacobian.
                           ...
                           call cntnzu(n, iwk(ipian), iwk(ipjan), nzsut) !can be skipped
                           ...
                           call odrv(n, iwk(ipian), iwk(ipjan), wk, iwk(ipr), iwk(ipic), nsp, iwk(ipisp), 1, iys)
                                └─ ! driver for sparse matrix reordering routines
                                   ...
                                   call md(n, ia, ja, max, isp(v), isp(l), isp(head), p, ip, isp(v), flag)
                                        └─ ! finds a minimum degree ordering
                                           ...
                                           ! initialization
                                           call mdi(n, ia,ja, max,v,l, head,last,next, mark,tag, flag)
                                           ...
!                                          form element ek from uneliminated neighbors of vk
                                           call mdm(vk, tail, v, l, last, next, mark)
!                                          purge inactive elements and do mass elimination
                                           call mdp(k, ek, tail, v, l, head, last, next, mark)
!                                          update degrees of uneliminated vertices in ek
                                           call mdu(ek, dmin, v, l, head, last, next, mark)
                                           ...
                                   ...
                                   !  symmetric reordering of sparse symmetric matrix.                                  ...
                                   call sro(n, ip, ia, ja, a, isp(tmp), isp(q), dflag)
                           ...  
!                          reorder jan and do symbolic lu factorization of matrix.
                           call cdrv(n,iwk(ipr),iwk(ipc),iwk(ipic),iwk(ipian),iwk(ipjan),wk(ipa),wk(ipa),wk(ipa),nsp,iwk(ipisp),wk(iprsp),iesp,5,iys)
                                └─ ! driver for subroutines for solving sparse nonsymmetric systems of linear equations (compressed pointer storage)
                                   ...
                                   ! reorders rows of a, leaving row order unchanged
                                   call nroc(n, ic, ia, ja, a, isp(il), rsp(ar), isp(iu), flag)
                                   ...
                                   ! symbolic ldu-factorization of nonsymmetric sparse matrix (compressed pointer storage)
                                   call nsfc(n, r, ic, ia, ja, jlmax, isp(il), isp(jl), isp(ijl), jumax, isp(iu), isp(jutmp), isp(iju), isp(q), isp(ira), isp(jra), isp(irac), isp(irl), isp(jrl), isp(iru), isp(jru),  flag)
                                   ...
                                   ! numerical ldu-factorization of sparse nonsymmetric matrix and solution of system of linear equations (compressed pointer storage)
                                   call nnfc(n, r, c, ic,  ia, ja, a, z, b, lmax, isp(il), isp(jl), isp(ijl), rsp(l), rsp(d), umax, isp(iu), isp(ju), isp(iju), rsp(u), rsp(row), rsp(tmp),  isp(irl), isp(jrl),  flag)
                                   ...
                                   ! numerical solution of sparse nonsymmetric system of linear equations given ldu-factorization (compressed pointer storage)
                                   call nnsc(n,  r, c, isp(il), isp(jl), isp(ijl), rsp(l), rsp(d), isp(iu), isp(ju), isp(iju), rsp(u), z, b, rsp(tmp))
                                   
                                   ! numeric solution of the transpose of a sparse nonsymmetric system of linear equations given lu-factorization (compressed pointer storage)
                                   call nntc(n,  r, c, isp(il), isp(jl), isp(ijl), rsp(l), rsp(d), isp(iu), isp(ju), isp(iju), rsp(u), z, b, rsp(tmp))
                                   ...
        end if
  
     else ! istate .eq. 3
  
        if(miter .eq. 1 .or. miter .eq. 2)then
           if(moss .eq. 2)then
!             temporarily load ewt if miter = 1 or 2 and moss = 2.
              call ewset (n, itol, rtol, atol, rwork(lyh), rwork(lewt))
              ...
           end if
!          iprep and prep do sparse matrix preprocessing if miter = 1 or 2.
           ...
           call iprep(neq, y, rwork, iwork(lia), iwork(lja), ipflag)
           ...
        end if
        ...
     end if
  end if
  
  ! for a continuation call with parameter changes (istate = 3) and  without parameter changes (istate = 2)
  if(istate .eq. 2 .or. istate .eq. 3)then
!    block d. for continuation calls only (istate = 2 or 3) and is to check stop conditions before taking a step.
     if(itask .eq. 1)then
        ! itask  = 1 for normal computation of output values of y at t = tout. see other itasks in lsodes top comments
        ...
           ! computes interpolated values of the vector yh and stores it in y
           call intdy (tout, 0, rwork(lyh), nyh, y, iflag)
        ...
        end if
     else if(itask .eq. 3)then
        ...
     else if(itask .eq. 4)then
        ...
           ! computes interpolated values of the vector yh and stores it in y
           call intdy (tout, 0, rwork(lyh), nyh, y, iflag)
        ...
     else if(itask .eq. 5)then
        ...
     end if
  
     if(itask .eq. 4 .or. itask .eq. 5)then
        ...
     end if
  
! BLOCK E. normally executed for all calls and contains the call to the one-step core integrator stode.
  do while(.true.)
     ...
     call ewset (n, itol, rtol, atol, rwork(lyh), rwork(lewt))
     ...
     ! stode performs one step of the integration of an initial value problem for a system of ordinary differential equations.
     call stode (neq, y, rwork(lyh), nyh, rwork(lyh), rwork(lewt), rwork(lsavf), rwork(lacor), rwork(lwm), rwork(lwm))
          └─ ...
             ! jstart = 0  perform the first step.
             !          .gt.0  take a new step continuing from the last.
             !          -1  take the next step with a new value of h, maxord, n, meth, miter, and/or matrix parameters.
             !          -2  take the next step with a new value of h, but with other inputs unchanged.
             if(jstart .eq. 0)then
                ...
                ! cfode is called to reset the coefficients of the method.
                call cfode(meth, elco, tesco)
                ! el vector and related constants are reset at the start of the problem.
                call order_changed()
  
             else if(jstart .eq. -1)then
                ! preliminaries needed when jstart = -1
                ...
                ! if the caller has changed meth, cfode is called to reset the coefficients of the method.
                ...
                call cfode(meth, elco, tesco)
                ...
                ! el vector and related constants are reset when the order nq is changed.
                call order_changed()
                ...
                ! if h is being changed, the h ratio rh is checked against rmax, hmin, and hmxi, and the yh array rescaled.
                call step_changed(rh, nyh, yh)
                
                ! The three subroutines above are called several times in stode
                ...
            else if(jstart .eq. -2 .and. h .ne. hold)then
                ...
            end if

            do while(.true.)
               ...
               do while(.not. exit1)
                  ...
                  call rhs(neq, tn, y, savf)
                  ...
                  if(ipup .gt. 0)then
!                    if indicated, the matrix p = i - h*el(1)*j is reevaluated and preprocessed before starting the corrector iteration.  
                     call prjs(neq, y, yh, nnyh, ewt, acor, savf, wm, iwm)
                          └─ ...
                             if(miter .eq. 3)then
                                ! construct a diagonal approximation to j and p.
                                ...
                                call rhs(neq, tn, y, wk(3))
                                ...
                             end if
                             
                             if(jok .eq. 0)then
                                ! miter = 1 or 2, and the jacobian is to be reevaluated.
                                if(miter .eq. 1)then
                                   ! call fjac, multiply by scalar, and add identity.
                                   ...
                                   call fjac(neq, tn, y, j, iwk(ipian), iwk(ipjan), ftem)
                                   ...
                                else ! miter == 2
                                   ! make ngp calls to f to approximate j and p.
                                   ...
                                   call rhs(neq, tn, y, ftem)
                                   ...
                                end if
                             else ! jok .eq. 1
                                ! reconstruct new p from old p.
                                ...
                             end if
                             ! do numerical factorization of p matrix.
                             ...
                             call cdrv(n,iwk(ipr),iwk(ipc),iwk(ipic),iwk(ipian),iwk(ipjan), wk(ipa),ftem,ftem,nsp,iwk(ipisp),wk(iprsp),iesp,2,iys)
                             ...
                     ...
                  end if
                  do while(.not. exit2)
                     if(miter .eq. 0)then
                        ! in case of functional iteration, update y directly from the result of the last function evaluation.
                        ... 
                     else
                        ! in case of chord method, compute corrector error, and solve linear system with that as right-hand side and p as coefficient matrix.
                        ...
                        call slss(wm, iwm, y, savf)
                             └─ ! manages the solution of the linear system arising from a chord iteration.
                             ...
                             call cdrv(n,iwk(ipr),iwk(ipc),iwk(ipic),iwk(ipian),iwk(ipjan),wk(ipa),x,x,nsp,iwk(ipisp),wk(iprsp),iesp,4,iersl)
                             ...
                        ...
                     end if
                     ...
                  end do
                  ...
               end do
               ...
            end do
            
     ! BLOCK F. handles the case of a successful return from the core integrator (kflag = 0).  test for stop conditions.
     ...
     if(itask .eq. 1) then
     ...
     else if(itask .eq. 2) then
     ...
     else if(itask .eq. 3) then
     ...
     else if(itask .eq. 4) then
!       see if tout or tcrit was reached. adjust h if necessary.
     ...
           call intdy (tout, 0, rwork(lyh), nyh, y, iflag)
     ...
     else if(itask .eq. 5) then
     ...
     end if
  end do